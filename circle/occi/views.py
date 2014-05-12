from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import View


class QueryInterface(View):

    def get(self, request, *args, **kwargs):
        response = HttpResponse("Hai!")
        response['yo'] = "as"
        return response

    def post(self, request, *args, **kwargs):
        response = HttpResponse(status=501)
        return response

    @method_decorator(csrf_exempt)  # decorator on post method doesn't work
    def dispatch(self, *args, **kwargs):
        return super(QueryInterface, self).dispatch(*args, **kwargs)
