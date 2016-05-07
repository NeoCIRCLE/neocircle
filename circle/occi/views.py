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
from forms import OcciAuthForm
from occi_infrastructure import Compute
from occi_utils import (OcciResourceInstanceNotExist,
                        OcciActionInvocationError,
                        OcciRequestNotValid,
                        OcciResourceCreationError,
                        OcciResourceDeletionError,
                        occi_response,
                        validate_request)
from occi_instances import ALL_KINDS, ALL_MIXINS, ALL_ACTIONS


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
        vms = (Instance.get_objects_with_level("user", request.user)
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
            vm = get_object_or_404(Instance.get_objects_with_level("user",
                                   user).filter(destroyed_at=None), pk=vmid)
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
        if not requestData["action"]:
            return occi_response({"error": "Action invocation rendering " +
                                  "is not supplied."},
                                 status=400)
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
