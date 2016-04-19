""" The views of the OCCI implementation of CIRCLE.
    These views handle the http requests of the API. """


from django.views.generic import View
from django.contrib.auth import logout
from django.http import HttpResponse, JsonResponse
from vm.models.instance import Instance
from common.models import HumanReadableException
from forms import OcciAuthForm
import json
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from occi_core import ENTITY_KIND


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

class TestView(View):
    """ TEST VIEW """
    def get(self, request, *args, **kwargs):
        return JsonResponse(ENTITY_KIND.render_as_json())
