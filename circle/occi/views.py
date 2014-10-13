from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View, DetailView

from vm.models import Instance

from .occi import (
    Compute,
    COMPUTE_KIND,
    COMPUTE_ACTIONS,
)


class QueryInterface(View):

    def get(self, request, *args, **kwargs):
        response = "Category: %s\n" % COMPUTE_KIND.render_values()
        for c in COMPUTE_ACTIONS:
            response += "Category: %s\n" % c.render_values()

        return HttpResponse(
            response,
            content_type="text/plain",
        )

    def post(self, request, *args, **kwargs):
        response = HttpResponse(status=501)
        return response

    @method_decorator(csrf_exempt)  # decorator on post method doesn't work
    def dispatch(self, *args, **kwargs):
        return super(QueryInterface, self).dispatch(*args, **kwargs)


class ComputeInterface(View):

    def get(self, request, *args, **kwargs):
        response = "\n".join([Compute(instance=i).render_location()
                             for i in Instance.active.all()])
        return HttpResponse(
            response,
            content_type="text/plain",
        )

    def post(self, request, *args, **kwargs):
        occi_attrs = None
        category = None
        for k, v in request.META.iteritems():
            if k.startswith("HTTP_X_OCCI_ATTRIBUTE"):
                occi_attrs = v.split(",")
            elif k.startswith("HTTP_CATEGORY") and category is None:
                category = v

        c = Compute(attrs=occi_attrs)
        response = HttpResponse()
        response['Location'] = c.location
        return response

    @method_decorator(csrf_exempt)  # decorator on post method doesn't work
    def dispatch(self, *args, **kwargs):
        return super(ComputeInterface, self).dispatch(*args, **kwargs)


class VmInterface(DetailView):
    model = Instance

    def get(self, request, *args, **kwargs):
        vm = self.get_object()
        c = Compute(instance=vm)
        return HttpResponse(
            c.render_body(),
            content_type="text/plain",
        )

    def post(self, request, *args, **kwargs):
        # actions, resource change
        pass

    @method_decorator(csrf_exempt)  # decorator on post method doesn't work
    def dispatch(self, *args, **kwargs):
        return super(VmInterface, self).dispatch(*args, **kwargs)

"""
test commands:
    curl 10.7.0.103:8080/occi/-/ -X GET

    curl 10.7.0.103:8080/occi/compute/ -X GET

    curl 10.7.0.103:8080/occi/compute/ -X POST
    --header "X-OCCI-Attribute: occi.compute.cores=2"
    --header "X-OCCI-Attribute: occi.compute.architecture=x86"
    --header "X-OCCI-Attribute: occi.compute.speed=1"
    --header "X-OCCI-Attribute: occi.compute.memory=1024" -I
"""
