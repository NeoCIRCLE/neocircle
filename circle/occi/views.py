from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View, DetailView

from firewall.models import Vlan
from vm.models import Instance, InstanceTemplate
from storage.models import Disk

from .occi import (
    Compute,
    Storage,
    Network,
    OsTemplate,
    StorageLink,
    COMPUTE_KIND,
    STORAGE_KIND,
    LINK_KIND,
    STORAGE_LINK_KIND,
    COMPUTE_ACTIONS,
    OS_TPL_MIXIN,
    NETWORK_KIND,
    IPNETWORK_MIXIN,
)


class CSRFExemptMixin(object):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(CSRFExemptMixin, self).dispatch(*args, **kwargs)


def get_post_data_from_request(request):
    """ Returns the post data in an array
    """
    post_data = []
    accept = request.META.get("HTTP_ACCEPT")
    if accept and accept.split(",")[0] == "text/occi":
        for k, v in request.META.iteritems():
            if k.startswith("HTTP_X_OCCI_ATTRIBUTE"):
                for l in v.split(","):
                    post_data.append("X-OCCI-Attribute: %s" % l.strip())
            if k.startswith("HTTP_CATEGORY"):
                for l in v.split(","):
                    post_data.append("Category: %s" % l.strip())
    else:  # text/plain or missing
        for l in request.readlines():
            if l:
                post_data.append(l.strip())
    return post_data


class QueryInterface(CSRFExemptMixin, View):

    def get(self, request, *args, **kwargs):
        response = "Category: %s\n" % COMPUTE_KIND.render_values()
        response += "Category: %s\n" % STORAGE_KIND.render_values()
        response += "Category: %s\n" % LINK_KIND.render_values()
        response += "Category: %s\n" % STORAGE_LINK_KIND.render_values()
        response += "Category: %s\n" % OS_TPL_MIXIN.render_values()
        response += "Category: %s\n" % NETWORK_KIND.render_values()
        response += "Category: %s\n" % IPNETWORK_MIXIN.render_values()
        for c in COMPUTE_ACTIONS:
            response += "Category: %s\n" % c.render_values()

        for t in InstanceTemplate.objects.all():
            response += OsTemplate(t).render_body()

        return HttpResponse(
            response,
            content_type="text/plain",
        )

    def post(self, request, *args, **kwargs):
        response = HttpResponse(status=501)
        return response


class ComputeInterface(CSRFExemptMixin, View):

    def get(self, request, *args, **kwargs):
        response = "\n".join([Compute(instance=i).render_location()
                             for i in Instance.active.all()])
        return HttpResponse(
            response,
            content_type="text/plain",
        )

    def post(self, request, *args, **kwargs):
        data = get_post_data_from_request(request)

        c = Compute.create_object(data=data)
        response = HttpResponse(
            "X-OCCI-Location: %s" % c.location,
            status=201,
            content_type="text/plain",
        )
        return response


class VmInterface(CSRFExemptMixin, DetailView):
    model = Instance

    def get_object(self):
        return get_object_or_404(Instance.objects.filter(destroyed_at=None),
                                 pk=self.kwargs['pk'])

    def get(self, request, *args, **kwargs):
        vm = self.get_object()
        c = Compute(instance=vm)
        return HttpResponse(
            c.render_body(),
            content_type="text/plain",
        )

    def post(self, request, *args, **kwargs):
        data = get_post_data_from_request(request)
        action = request.GET.get("action")
        vm = self.get_object()
        if action:
            Compute(instance=vm).trigger_action(data)
        return HttpResponse()

    def delete(self, request, *args, **kwargs):
        vm = self.get_object()
        Compute(instance=vm).delete()

        return HttpResponse()


class OsTplInterface(CSRFExemptMixin, View):

    def get(self, request, *args, **kwargs):
        response = "\n".join([OsTemplate(template=t).render_location()
                             for t in InstanceTemplate.objects.all()])
        return HttpResponse(
            response,
            content_type="text/plain",
        )

    def post(self, request, *args, **kwargs):
        pass


class StorageInterface(CSRFExemptMixin, View):

    def get(self, request, *args, **kwargs):
        response = "\n".join([Storage(disk=d).render_location()
                             for d in Disk.objects.filter(destroyed=None)])
        return HttpResponse(
            response,
            content_type="text/plain",
        )

    def post(self, request, *args, **kwargs):
        data = get_post_data_from_request(request)

        d = Storage.create_object(data=data)
        response = HttpResponse(
            "X-OCCI-Location: %s" % d.location,
            status=201,
            content_type="text/plain",
        )
        return response


class DiskInterface(CSRFExemptMixin, DetailView):
    model = Disk

    def get(self, request, *args, **kwargs):
        disk = self.get_object()
        c = Storage(disk=disk)
        return HttpResponse(
            c.render_body(),
            content_type="text/plain",
        )

    def post(self, request, *args, **kwargs):
        # TODO actions (we only support resize)
        data = get_post_data_from_request(request)
        action = request.GET.get("action")
        disk = self.get_object()
        if action:
            Storage(disk=disk).trigger_action(data)
        return HttpResponse()

    def delete(self, request, *args, **kwargs):
        Storage(disk=self.get_object()).delete()
        return HttpResponse("")


class StorageLinkInterface(CSRFExemptMixin, View):

    def get_vm_and_disk(self):
        vm = get_object_or_404(Instance.objects.filter(destroyed_at=None),
                               pk=self.kwargs['vm_pk'])
        disk = get_object_or_404(Disk.objects.filter(destroyed=None),
                                 pk=self.kwargs['disk_pk'])

        if disk not in vm.disks.all():
            raise Http404

        return vm, disk

    def get(self, request, *args, **kwargs):
        vm, disk = self.get_vm_and_disk()
        sl = StorageLink(instance=vm, disk=disk)
        return HttpResponse(
            sl.render_as_category(),
            content_type="text/plain",
        )

    def post(self, request, *args, **kwargs):
        # we don't support actions for storagelinks
        # (they don't even exist in the model)
        if request.GET.get("action"):
            return HttpResponse("", status=500)

        data = get_post_data_from_request(request)
        sl = StorageLink.create_object(data=data)
        if sl:
            response = HttpResponse(
                "X-OCCI-Location: %s" % sl.location,
                status=201,
                content_type="text/plain",
            )
            return response
        else:
            return HttpResponse("VM or Storage does not exist.", status=500)

    def delete(self, request, *args, **kwargs):
        vm, disk = self.get_vm_and_disk()
        sl = StorageLink(instance=vm, disk=disk)

        sl.delete()
        return HttpResponse("")


class NetworkInterface(CSRFExemptMixin, View):

    def get(self, request, *args, **kwargs):
        response = "\n".join([Network(vlan=v).render_location()
                             for v in Vlan.objects.all()])
        return HttpResponse(
            response,
            content_type="text/plain",
        )

    def post(self, request, *args, **kwargs):
        pass  # we don't really want to create networks via OCCI yet


class VlanInterface(CSRFExemptMixin, DetailView):
    model = Vlan
    slug_field = 'vid'
    slug_url_kwarg = 'vid'

    def get(self, request, *args, **kwargs):
        vlan = self.get_object()
        c = Network(vlan=vlan)
        return HttpResponse(
            c.render_body(),
            content_type="text/plain",
        )

    def post(self, request, *args, **kwargs):
        pass  # no actions

    def delete(self, request, *args, **kwargs):
        vm = self.get_object()
        Compute(instance=vm).delete()

        return HttpResponse()