# Copyright 2017 Budapest University of Technology and Economics (BME IK)
#
# This file is part of CIRCLE Cloud.
#
# CIRCLE is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# CIRCLE is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along
# with CIRCLE.  If not, see <http://www.gnu.org/licenses/>.


""" The views of the OCCI implementation of CIRCLE.
    These views handle the http requests of the API. """


import json
from django.views.generic import View
from django.contrib.auth import logout
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from vm.models.instance import Instance, InstanceTemplate
from storage.models import Disk
from firewall.models import Vlan
from forms import OcciAuthForm
from occi_infrastructure import Compute, Storage, Network
from occi_utils import (OcciResourceInstanceNotExist,
                        OcciActionInvocationError,
                        OcciRequestNotValid,
                        OcciResourceCreationError,
                        OcciResourceDeletionError,
                        occi_response,
                        validate_request)
from occi_instances import ALL_KINDS, ALL_MIXINS, ALL_ACTIONS
from common.models import HumanReadableException

import logging
log = logging.getLogger(__name__)


class OcciLoginView(View):
    """ Authentication for the usage of the OCCI api.
        This view responds with 200 and the access token in a Cookie if the
        authentication succeeded, and with 400 if the provided username and
        password is not valid. """
    @method_decorator(ensure_csrf_cookie)
    def get(self, request, *args, **kwargs):
        """ Returns a response with a cookie to be used for requests other
            than get. """
        result = {"result": "OK"}
        return occi_response(result)

    def post(self, request, *args, **kwargs):
        """ Returns a response with a cookie to be used for the OCCI api
            requests. """
        data = json.loads(request.body.decode("utf-8"))
        log.error(data)
        print(data)
        form = OcciAuthForm(data=data, request=request)
        if form.is_valid():
            result = {"result": "OK"}
            return occi_response(result)
        else:
            errors = dict([(k, [unicode(e) for e in v])
                           for k, v in form.errors.items()])
            result = {"result": "ERROR", "errors": errors["__all__"]}
            return occi_response(result, status=400)


class OcciLogoutView(View):
    """ Logout """

    def get(self, request, *args, **kwargs):
        logout(request)
        result = {"result": "OK"}
        return occi_response(result)


class OcciQueryInterfaceView(View):
    """ The view of the OCCI query interface """
    @method_decorator(ensure_csrf_cookie)
    def get(self, request, *args, **kwargs):
        try:
            validate_request(request)
        except OcciRequestNotValid as e:
            return e.response
        result = {"kinds": [], "mixins": [], "actions": []}
        for kind in ALL_KINDS():
            result["kinds"].append(kind.render_as_json())
        for mixin in ALL_MIXINS(request.user):
            result["mixins"].append(mixin.render_as_json())
        for action in ALL_ACTIONS():
            result["actions"].append(action.render_as_json())
        return occi_response(result)

    def post(self, request, *args, **kwargs):
        return occi_response({"error": "User defined mixins are not " +
                              "supported."}, status=405)

    def delete(self, request, *args, **kwargs):
        return occi_response({"error": "User defined mixins are not " +
                              "supported."}, status=405)

    def put(self, request, *args, **kwargs):
        return occi_response({"error": "Put method is not defined on the " +
                              "query interface."}, status=400)


class OcciComputeCollectionView(View):
    @method_decorator(ensure_csrf_cookie)
    def get(self, request, *args, **kwargs):
        try:
            validate_request(request)
        except OcciRequestNotValid as e:
            return e.response
        vms = (Instance.get_objects_with_level("owner", request.user)
               .filter(destroyed_at=None))
        json = {"resources": []}
        for vm in vms:
            json["resources"].append(Compute(vm).render_as_json())
        return occi_response(json)

    def put(self, request, *args, **kwargs):
        # TODO: vm creation
        return occi_response({"message": "TODO"})
        try:
            Instance.create_from_template(
                InstanceTemplate.objects.get(pk=1), request.user)
        except Exception:
            return occi_response({"test": "tset"})
        return occi_response({})


class OcciComputeView(View):
    """ View of a compute instance """

    def get_vm_object(self, user, vmid):
        try:
            vm = get_object_or_404(Instance.get_objects_with_level(
                "owner", user).filter(destroyed_at=None), pk=vmid)
        except Http404:
            raise OcciResourceInstanceNotExist()
        return Compute(vm)

    @method_decorator(ensure_csrf_cookie)
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated():
            return occi_response({"error": "Authentication required."},
                                 status=403)
        try:
            compute = self.get_vm_object(request.user, kwargs["id"])
        except OcciResourceInstanceNotExist as e:
            return e.response
        return occi_response(compute.render_as_json(), charset="utf-8")

    def post(self, request, *args, **kwargs):
        requestData = json.loads(request.body.decode("utf-8"))
        if "action" in requestData:
            try:
                compute = self.get_vm_object(request.user, kwargs["id"])
            except OcciResourceInstanceNotExist as e:
                return e.response
            try:
                compute.invoke_action(request.user,
                                      requestData.get("action", None),
                                      requestData.get("attributes", None))
            except OcciActionInvocationError as e:
                return e.response
            return occi_response(compute.render_as_json(), status=200)
        elif "attributes" in requestData:
            attrs = requestData["attributes"]
            try:
                vm = get_object_or_404(Instance.get_objects_with_level(
                    "owner", request.user).filter(destroyed_at=None),
                    pk=kwargs["id"])
            except Http404:
                return OcciResourceInstanceNotExist().response
            num_cores = attrs.get("occi.compute.cores", vm.num_cores)
            ram_size = (
                attrs.get("occi.compute.memory", vm.ram_size / 1024.0) * 1024)
            priority = attrs.get("occi.compute.share", vm.priority)
            try:
                vm.resources_change(
                    user=request.user,
                    num_cores=num_cores,
                    ram_size=ram_size,
                    max_ram_size=vm.max_ram_size,
                    priority=priority
                )
            except HumanReadableException as e:
                log.warning(e.get_user_text())
            return occi_response(Compute(vm).render_as_json(), status=200)
        return occi_response({"error": "Bad request"}, status=400)

    def put(self, request, *args, **kwargs):
        # checking if the requested resource exists
        try:
            self.get_vm_object(request.user, kwargs["id"])
        except OcciResourceInstanceNotExist:
            # there has to be a mixins array in the provided rendering
            data_keys = ["mixins"]
            try:
                requestData = validate_request(request, True, True,
                                               data_keys=data_keys)
            except OcciRequestNotValid as e:
                return e.response
            ostpl = "http://circlecloud.org/occi/templates/os#os_template_"
            for mixin in requestData["mixins"]:
                if ostpl in mixin:
                    tpl_id = int(mixin.replace(ostpl, ""))
                    try:
                        template = get_object_or_404(
                            InstanceTemplate.get_objects_with_level(
                                "user", request.user), pk=tpl_id)
                    except Http404:
                        return occi_response({"error": "Template does not" +
                                              "exist."})
                    try:
                        vm = Instance.create_from_template(template,
                                                           request.user)
                    except:
                        return OcciResourceCreationError().response
                    compute = Compute(vm)
                    return occi_response(compute.render_as_json())
        # TODO: update compute instance
        return occi_response({"error": "Update of compute instances is " +
                              "not implemented."}, status=501)

    def delete(self, request, *args, **kwargs):
        try:
            compute = self.get_vm_object(request.user, kwargs["id"])
        except OcciResourceInstanceNotExist as e:
            return e.response
        try:
            compute.vm.destroy(user=request.user)
        except:
            return OcciResourceDeletionError().response
        return occi_response({"result": "Compute instance deleted."})


class OcciStorageCollectionView(View):

    @method_decorator(ensure_csrf_cookie)
    def get(self, request, *args, **kwargs):
        try:
            validate_request(request)
        except OcciRequestNotValid as e:
            return e.response
        vms = (Instance.get_objects_with_level("owner", request.user)
               .filter(destroyed_at=None))
        json = {"resources": []}
        for vm in vms:
            disks = vm.disks.all()
            for disk in disks:
                json["resources"].append(Storage(disk).render_as_json())
        return occi_response(json)

    def put(self, request, *args, **kwargs):
        return occi_response({"message": "Not supported."}, status=501)


class OcciStorageView(View):
    """ View of a storage instance """

    def get_disk_object(self, user, diskid):
        try:
            disk = get_object_or_404(Disk, pk=diskid)
        except Http404:
            raise OcciResourceInstanceNotExist()

        diskvms = disk.instance_set.all()
        uservms = Instance.get_objects_with_level(
            "user", user).filter(destroyed_at=None)
        if len(diskvms & uservms) > 0:
            return Storage(disk)
        raise OcciResourceInstanceNotExist()

    @method_decorator(ensure_csrf_cookie)
    def get(self, request, *args, **kwargs):
        try:
            validate_request(request)
        except OcciRequestNotValid as e:
            return e.response
        try:
            disk = self.get_disk_object(request.user, kwargs["id"])
        except OcciResourceInstanceNotExist as e:
            return e.response
        return occi_response(disk.render_as_json(), charset="utf-8")

    def post(self, request, *args, **kwargs):
        requestData = json.loads(request.body.decode("utf-8"))
        if "action" not in requestData:
            return occi_response(
                {
                    "error": ("Storage pratial update is not supported. " +
                              "Action invocation rendering must be supplied."),
                },
                status=400
            )
        try:
            storage = self.get_disk_object(request.user, kwargs["id"])
        except OcciResourceInstanceNotExist as e:
            return e.response
        try:
            storage.invoke_action(request.user,
                                  requestData.get("action", None),
                                  requestData.get("attributes", None))
        except OcciActionInvocationError as e:
            return e.response
        return occi_response(storage.render_as_json(), status=200)


class OcciNetworkCollectionView(View):
    @method_decorator(ensure_csrf_cookie)
    def get(self, request, *args, **kwargs):
        try:
            validate_request(request)
        except OcciRequestNotValid as e:
            return e.response
        vlans = (Vlan.get_objects_with_level("owner", request.user))
        json = {"resources": []}
        for vlan in vlans:
            json["resources"].append(Network(vlan).render_as_json())
        return occi_response(json)


class OcciNetworkView(View):
    """ View of a compute instance """

    def get_vlan_object(self, user, vlanid):
        try:
            vlan = get_object_or_404(Vlan.get_objects_with_level(
                "user", user), pk=vlanid)
        except Http404:
            raise OcciResourceInstanceNotExist()
        return Network(vlan)

    @method_decorator(ensure_csrf_cookie)
    def get(self, request, *args, **kwargs):
        try:
            validate_request(request)
        except OcciRequestNotValid as e:
            return e.response
        try:
            network = self.get_vlan_object(request.user, kwargs["id"])
        except OcciResourceInstanceNotExist as e:
            return e.response
        return occi_response(network.render_as_json(), charset="utf-8")

    def post(self, request, *args, **kwargs):
        requestData = json.loads(request.body.decode("utf-8"))
        if "action" not in requestData:
            return occi_response(
                {
                    "error": ("Network partial update is not supported. " +
                              "Action invocation rendering must be supplied."),
                },
                status=400
            )
        try:
            network = self.get_vlan_object(request.user, kwargs["id"])
        except OcciResourceInstanceNotExist as e:
            return e.response
        try:
            network.invoke_action(request.user,
                                  requestData.get("action", None),
                                  requestData.get("attributes", None))
        except OcciActionInvocationError as e:
            return e.response
        return occi_response(network.render_as_json(), status=200)
