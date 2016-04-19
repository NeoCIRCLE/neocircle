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
        data = json.loads(request.body.decode("utf-8"))
        """ Returns a response with a cookie to be used for the OCCI api
            requests. """
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


class OcciComputeCollectionView(View):
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
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated():
            return HttpResponse(status=403)
        try:
            vm = get_object_or_404(Instance.get_objects_with_level("user",
                                   request.user), pk=kwargs['id'])
        except Http404:
            return JsonResponse({"error": "There is no instance with the" +
                                 " id " + kwargs['id'] + "."}, status=400)
        compute = Compute(vm)
        return JsonResponse(compute.render_as_json(), charset="utf-8")
