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
from vm.models.instance import Instance, InstanceTemplate
from storage.models import Disk
from firewall.models import Vlan
from network.models import Vxlan
from occi.forms import OcciAuthForm
from occi.infrastructure import (Compute, Storage, Network, StorageLink,
                                 NetworkInterface,)
from occi.utils import (OcciResourceInstanceNotExist,
                        OcciActionInvocationError,
                        OcciRequestNotValid,
                        OcciResourceCreationError,
                        OcciResourceDeletionError,
                        occi_response,
                        validate_request_data)
from occi.instances import ALL_KINDS, ALL_MIXINS, ALL_ACTIONS
from common.models import HumanReadableException
from occi.mixins import OcciViewMixin, EnsureCsrfTokenMixin

import logging
log = logging.getLogger(__name__)


class OcciLoginView(EnsureCsrfTokenMixin, View):
    """ Authentication for the usage of the OCCI api.
        This view responds with 200 and the access token in a Cookie if the
        authentication succeeded, and with 400 if the provided username and
        password is not valid. """

    def get(self, request, *args, **kwargs):
        """ Returns a response with a cookie to be used for requests other
            than get. """
        result = {"result": "OK"}
        return occi_response(result)

    def post(self, request, *args, **kwargs):
        """ Returns a response with a cookie to be used for the OCCI api
            requests. """
        data = json.loads(request.body.decode("utf-8"))
        form = OcciAuthForm(data=data, request=request)
        if form.is_valid():
            result = {"result": "OK"}
            return occi_response(result)
        else:
            errors = dict([(k, [unicode(e) for e in v])
                           for k, v in form.errors.items()])
            result = {"result": "ERROR", "errors": errors["__all__"]}
            return occi_response(result, status=400)


class OcciLogoutView(EnsureCsrfTokenMixin, View):
    """ Logout """

    def get(self, request, *args, **kwargs):
        logout(request)
        result = {"result": "OK"}
        return occi_response(result)


class OcciQueryInterfaceView(OcciViewMixin, View):
    """ The view of the OCCI query interface """

    def get(self, request, *args, **kwargs):
        result = {"kinds": [], "mixins": [], "actions": []}
        for kind in ALL_KINDS():
            result["kinds"].append(kind.as_dict())
        result["mixins"] = [mixin.as_dict() for mixin in
                            ALL_MIXINS(request.user)]
        result["actions"] = [action.as_dict()
                             for action in ALL_ACTIONS()]
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


class OcciComputeCollectionView(OcciViewMixin, View):

    def get(self, request, *args, **kwargs):
        resources = [Compute(vm).as_dict()
                     for vm in Instance.get_objects_with_level(
                     "owner", request.user).filter(destroyed_at=None)]
        return occi_response({"resources": resources})

    def put(self, request, *args, **kwargs):
        # TODO: vm creation
        return occi_response({"message": "TODO"})


class OcciComputeView(OcciViewMixin, View):
    """ View of a compute instance """

    def get_vm_object(self, user, vmid):
        try:
            vm = get_object_or_404(Instance.get_objects_with_level(
                "owner", user).filter(destroyed_at=None), pk=vmid)
        except Http404:
            raise OcciResourceInstanceNotExist()
        return Compute(vm)

    def get(self, request, *args, **kwargs):
        try:
            compute = self.get_vm_object(request.user, kwargs["id"])
        except OcciResourceInstanceNotExist as e:
            return e.response
        return occi_response(compute.as_dict(), charset="utf-8")

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
            return occi_response(compute.as_dict(), status=200)
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
            return occi_response(Compute(vm).as_dict(), status=200)
        return occi_response({"error": "Bad request"}, status=400)

    def put(self, request, *args, **kwargs):
        # checking if the requested resource exists
        try:
            self.get_vm_object(request.user, kwargs["id"])
        except OcciResourceInstanceNotExist:
            # there has to be a mixins array in the provided rendering
            data_keys = ["mixins"]
            try:
                requestData = validate_request_data(request,
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
                    except Exception:
                        return OcciResourceCreationError().response
                    compute = Compute(vm)
                    return occi_response(compute.as_dict())
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
        except Exception:
            return OcciResourceDeletionError().response
        return occi_response({"result": "Compute instance deleted."})


class OcciStorageCollectionView(OcciViewMixin, View):

    def get(self, request, *args, **kwargs):
        vms = (Instance.get_objects_with_level("owner", request.user)
               .filter(destroyed_at=None))
        json = {"resources": []}
        for vm in vms:
            disks = vm.disks.all()
            for disk in disks:
                json["resources"].append(Storage(disk).as_dict())
        return occi_response(json)

    def put(self, request, *args, **kwargs):
        return occi_response({"message": "Not supported."}, status=501)


class OcciStorageView(OcciViewMixin, View):
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

    def get(self, request, *args, **kwargs):
        try:
            disk = self.get_disk_object(request.user, kwargs["id"])
        except OcciResourceInstanceNotExist as e:
            return e.response
        return occi_response(disk.as_dict(), charset="utf-8")

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
        return occi_response(storage.as_dict(), status=200)

    def put(self, request, *args, **kwargs):
        return OcciResourceCreationError(
            message="Storage creation is not supported at this uri. " +
            "Please use the compute instances' actions!"
        ).response


class OcciNetworkCollectionView(OcciViewMixin, View):

    def get(self, request, *args, **kwargs):
        vlans = Vlan.get_objects_with_level("owner", request.user)
        vxlans = Vxlan.get_objects_with_level("owner", request.user)
        json = {"resources": []}
        for vlan in vlans:
            json["resources"].append(Network(vlan, type="vlan").as_dict())
        for vxlan in vxlans:
            json["resources"].append(Network(vxlan, type="vxlan").as_dict())
        return occi_response(json)


class OcciNetworkView(OcciViewMixin, View):
    """ View of a compute instance """

    def get_vlan_object(self, user, kwargs):
        type = kwargs.get("type", "vlan")
        model = Vxlan if type == "vxlan" else Vlan
        try:
            object = get_object_or_404(model.get_objects_with_level(
                "user", user), pk=kwargs["id"])
        except Http404:
            raise OcciResourceInstanceNotExist()
        return Network(object, type=type)

    def get(self, request, *args, **kwargs):
        try:
            network = self.get_vlan_object(request.user, kwargs)
        except OcciResourceInstanceNotExist as e:
            return e.response
        return occi_response(network.as_dict(), charset="utf-8")

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
            network = self.get_vlan_object(request.user, kwargs)
        except OcciResourceInstanceNotExist as e:
            return e.response
        try:
            network.invoke_action(request.user,
                                  requestData.get("action", None),
                                  requestData.get("attributes", None))
        except OcciActionInvocationError as e:
            return e.response
        return occi_response(network.as_dict(), status=200)


class OcciStoragelinkCollectionView(OcciViewMixin, View):
    """ View of all storage link instances of the user """

    def get(self, request, *args, **kwargs):
        vms = (Instance.get_objects_with_level("owner", request.user)
               .filter(destroyed_at=None))
        links = [StorageLink(Compute(vm), Storage(disk)).as_dict()
                 for vm in vms for disk in vm.disks.all()]
        return occi_response({"links": links})


class OcciStoragelinkView(OcciViewMixin, View):
    """ VIew of a storage link instance """

    def get(self, request, *args, **kwargs):
        try:
            vm = get_object_or_404(Instance.get_objects_with_level(
                "owner", request.user).filter(destroyed_at=None),
                pk=kwargs["computeid"])
        except Http404:
            return OcciResourceInstanceNotExist().response
        try:
            disk = vm.disks.get(pk=kwargs["storageid"])
        except Disk.DoesNotExist:
            return OcciResourceInstanceNotExist().response
        return occi_response(
            StorageLink(Compute(vm), Storage(disk)).as_dict())


class OcciNetworkInterfaceCollectionView(OcciViewMixin, View):
    """ View of network interface instances of a user """

    def get(self, request, *args, **kwargs):
        vms = (Instance.get_objects_with_level("owner", request.user)
               .filter(destroyed_at=None))
        links = []
        for vm in vms:
            for nwi in vm.interface_set.all():
                net = nwi.vxlan if nwi.vxlan else nwi.vlan
                type = "vxlan" if nwi.vxlan else "vlan"
                links = NetworkInterface(Compute(vm),
                                         Network(net, type)).as_dict()
        return occi_response({"links": links})


class OcciNetworkInterfaceView(OcciViewMixin, View):
    """ View of a network interface instance """

    def get_compute_object(self, user, vmid):
        try:
            vm = get_object_or_404(Instance.get_objects_with_level(
                "owner", user).filter(destroyed_at=None), pk=vmid)
        except Http404:
            raise OcciResourceInstanceNotExist()
        return Compute(vm)

    def get_network_object(self, user, id, type):
        model = Vxlan if type == "vxlan" else Vlan
        try:
            object = get_object_or_404(model.get_objects_with_level(
                "user", user), pk=id)
        except Http404:
            raise OcciResourceInstanceNotExist()
        return Network(object, type)

    def get_networkinterface_object(self, user, kwargs):
        vmid = kwargs["computeid"]
        netid = kwargs["networkid"]
        type = kwargs["type"]
        compute = self.get_compute_object(user, vmid)
        try:
            if type == "vxlan":
                net = compute.vm.interface_set.get(vxlan__pk=netid).vxlan
            else:
                net = compute.vm.interface_set.get(vlan__pk=netid).vlan
        except Exception:
            raise OcciResourceInstanceNotExist()
        return NetworkInterface(compute, Network(net, type))

    def get(self, request, *args, **kwargs):
        try:
            nic = self.get_networkinterface_object(request.user, kwargs)
        except OcciResourceInstanceNotExist as e:
            return e.response
        return occi_response(nic.as_dict())

    def post(self, request, *args, **kwargs):
        requestData = json.loads(request.body.decode("utf-8"))
        if "action" in requestData:
            try:
                nif = self.get_networkinterface_object(request.user, kwargs)
            except OcciResourceInstanceNotExist as e:
                return e.response
            try:
                nif.invoke_action(request.user,
                                  requestData.get("action", None),
                                  requestData.get("attributes", None))
            except OcciActionInvocationError as e:
                return e.response
            return occi_response(nif.as_dict(), status=200)
        return OcciActionInvocationError().response

    def put(self, request, *args, **kwargs):
        netid = kwargs["network"]
        nettype = kwargs["type"]
        compute = self.get_compute_object(request.user, kwargs["computeid"])
        network = self.get_network_object(request.user, netid, nettype)
        try:
            if nettype == "vxlan":
                compute.vm.add_user_interface(user=request.user,
                                              vxlan=network.vlan)
            else:
                compute.vm.add_interface(user=request.user, vlan=network.vlan)
        except HumanReadableException as e:
            return OcciResourceCreationError(
                message=e.get_user_text()).response
        except Exception as e:
            return OcciResourceCreationError(message=unicode(e)).response
        nif = NetworkInterface(compute, network)
        return occi_response(nif.as_dict())

    def delete(self, request, *args, **kwargs):
        netid = kwargs["network"]
        nettype = kwargs["type"]
        compute = self.get_compute_object(request.user, kwargs["computeid"])
        network = self.get_network_object(request.user, netid, nettype)
        try:
            if nettype == "vxlan":
                interface = compute.vm.interface_set.get(vxlan=network.vlan)
            else:
                interface = compute.vm.interface_set.get(vlan=network.vlan)
        except Exception:
            return OcciResourceInstanceNotExist().response
        try:
            from firewall.models import Host
            from vm.models.network import Interface
            hc = Host.objects.filter(mac=interface.host.mac).count()
            ic = Interface.objects.filter(host__mac=interface.host.mac).count()
            if nettype == "vxlan":
                compute.vm.remove_user_interface(user=request.user,
                                                 interface=interface)
            else:
                compute.vm.remove_interface(user=request.user,
                                            interface=interface)
        except HumanReadableException as e:
            return OcciResourceDeletionError(
                message=e.get_user_text()).response
        except Exception:
            from firewall.models import Host
            from vm.models.network import Interface
            hc = Host.objects.filter(mac=interface.host.mac).count()
            ic = Interface.objects.filter(host__mac=interface.host.mac).count()
            return occi_response({"host": hc, "interface": ic})
        return occi_response({"status": "ok"})
