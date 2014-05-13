from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import View

from .occi import (
    COMPUTE_KIND,
    COMPUTE_ACTIONS,
)


class QueryInterface(View):

    def get(self, request, *args, **kwargs):
        response = "Category: %s\n" % COMPUTE_KIND.render_values()
        for c in COMPUTE_ACTIONS:
            response += "Category: %s\n" % c.render_values()

        return HttpResponse(response)

    def post(self, request, *args, **kwargs):
        response = HttpResponse(status=501)
        return response

    @method_decorator(csrf_exempt)  # decorator on post method doesn't work
    def dispatch(self, *args, **kwargs):
        return super(QueryInterface, self).dispatch(*args, **kwargs)
