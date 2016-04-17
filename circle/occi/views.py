""" The views of the OCCI implementation of CIRCLE.
    These views handle the http requests of the API. """


from django.views.generic import View
from django.contrib.auth import logout
from django.http import HttpResponse, JsonResponse
from vm.models.instance import Instance
from common.models import HumanReadableException
from forms import OcciAuthForm
import json


# TODO: csrf token
class OcciLoginView(View):
    """ Authentication for the usage of the OCCI api.
        This view responds with 200 and the access token in a Cookie if the
        authentication succeeded, and with 400 if the provided username and
        password is not valid. """
    def get(self, request, *args, **kwargs):
        """ Returns a response with a cookie to be used for requests other
            than get. """
        result = {"result": "OK"}
        return JsonResponse(result)

    def post(self, request, *args, **kwargs):
        data = json.loads(request.body.decode("utf-8"))
        """ Returns a response with a cookie to be used for the OCCI api
            requests. """
        form = OcciAuthForm(data=data, request=request)
        if form.is_valid():
            result = {"result": "OK"}
            return JsonResponse(result)
        else:
            errors = dict([(k, [unicode(e) for e in v])
                           for k, v in form.errors.items()])
            result = {"result": "ERROR", "errors": errors["__all__"]}
            return JsonResponse(result, status=400)


class OcciLogoutView(View):
    """ Logout """
    def get(self, request, *args, **kwargs):
        logout(request)
        result = {"result": "OK"}
        return JsonResponse(result)


class WakeUpVM(View):
    """ A test service which gets a VM to wake up """
    def get(self, request, *args, **kwargs):
        vm = Instance.objects.get(pk=6)
        try:
            vm.wake_up(user=request.user)
        except HumanReadableException as e:
            return HttpResponse(e.get_user_text(), status=400)
        return HttpResponse("Virtual machine waked up")


class SleepVM(View):
    """ A test service which gets a VM to sleep """
    def get(self, request, *args, **kwargs):
        vm = Instance.objects.get(pk=6)
        try:
            vm.sleep(user=request.user)
        except HumanReadableException as e:
            return HttpResponse(e.get_user_text(), status=400)
        return HttpResponse("Virtual machine fell asleep")


class ComputeListView(View):
    """ OCCI 1.2 - HTTP protocol - Collections - Compute """
    def get(self, request, *args, **kwargs):
        pass


class ComputeView(View):
    pass
