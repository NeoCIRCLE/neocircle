""" The views of the OCCI implementation of CIRCLE.
    These views handle the http requests of the API. """


import json
from django.views.generic import View
from django.contrib.auth import logout
from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from vm.models.instance import Instance
from forms import OcciAuthForm
from occi_infrastructure import Compute
from occi_utils import (OcciResourceInstanceNotExist,
                        OcciActionInvocationError)
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
        return JsonResponse(result, charset="utf-8")

    def post(self, request, *args, **kwargs):
        """ Returns a response with a cookie to be used for the OCCI api
            requests. """
        data = json.loads(request.body.decode("utf-8"))
        form = OcciAuthForm(data=data, request=request)
        if form.is_valid():
            result = {"result": "OK"}
            return JsonResponse(result, charset="utf-8")
        else:
            errors = dict([(k, [unicode(e) for e in v])
                           for k, v in form.errors.items()])
            result = {"result": "ERROR", "errors": errors["__all__"]}
            return JsonResponse(result, status=400, charset="utf-8")


class OcciLogoutView(View):
    """ Logout """
    def get(self, request, *args, **kwargs):
        logout(request)
        result = {"result": "OK"}
        return JsonResponse(result, charset="utf-8")


class OcciQueryInterfaceView(View):
    """ The view of the OCCI query interface """
    @method_decorator(ensure_csrf_cookie)
    def get(self, request, *args, **kwargs):
        result = {"kinds": [], "mixins": [], "actions": []}
        for kind in ALL_KINDS():
            result["kinds"].append(kind.render_as_json())
        for mixin in ALL_MIXINS():
            result["mixins"].append(mixin.render_as_json())
        for action in ALL_ACTIONS():
            result["actions"].append(action.render_as_json())
        return JsonResponse(result, charset="utf-8")


class OcciComputeCollectionView(View):
    @method_decorator(ensure_csrf_cookie)
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated():
            return HttpResponse(status=403)
        vms = (Instance.get_objects_with_level("user", request.user)
               .filter(destroyed_at=None))
        json = {"resources": []}
        for vm in vms:
            json["resources"].append(Compute(vm).render_as_json())
        return JsonResponse(json, charset="utf-8")


class OcciComputeView(View):
    """ View of a compute instance """
    def get_vm_object(self, request, vmid):
        try:
            vm = get_object_or_404(Instance.get_objects_with_level("user",
                                   request.user), pk=vmid)
        except Http404:
            raise OcciResourceInstanceNotExist()
        return Compute(vm)

    @method_decorator(ensure_csrf_cookie)
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated():
            return HttpResponse(status=403)
        try:
            compute = self.get_vm_object(request, kwargs["id"])
        except OcciResourceInstanceNotExist as e:
            return e.json_response
        return JsonResponse(compute.render_as_json(), charset="utf-8")

    def post(self, request, *args, **kwargs):
        requestData = json.loads(request.body.decode("utf-8"))
        # TODO post request w/o action, compute creation
        if not requestData["action"]:
            return HttpResponse(status=404)
        try:
            compute = self.get_vm_object(request, kwargs["id"])
        except OcciResourceInstanceNotExist as e:
            return e.response
        try:
            compute.invoke_action(request.user,
                                  requestData.get("action", None),
                                  requestData.get("attributes", None))
        except OcciActionInvocationError as e:
            return e.response
        # TODO: proper return value
        return JsonResponse(compute.render_as_json(), status=200)
