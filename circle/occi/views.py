import logging

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View, DetailView

from common.models import HumanReadableException
from firewall.models import Vlan
from vm.models import Instance, InstanceTemplate, Interface
from storage.models import Disk

from .occi import (
    Compute,
    Storage,
    Network,
    NetworkInterface,
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
    NETWORK_INTERFACE_KIND,
    IPNETWORK_INTERFACE_MIXIN,
)

logger = logging.getLogger(__name__)


class CSRFExemptMixin(object):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        try:
            return super(CSRFExemptMixin, self).dispatch(*args, **kwargs)
        except HumanReadableException as e:
            return HttpResponse(e.get_user_text(), status=400)

class OCCIPostDataAsListMixin(object):

    def get_post_data(self, request):
        """ Returns the post data in an array
        """
        post_data = []
        accept = request.META.get("HTTP_ACCEPT")
        if accept and accept.split(",")[0] == "text/occi":
            post_data = self._parse_from_header(request)
        else:  # text/plain or missing
            for l in request.readlines():
                if l:
                    post_data.append(l.strip())
        return post_data

    def _parse_from_header(self, request):
        post_data = []
        for k, v in request.META.iteritems():
            if k.startswith("HTTP_X_OCCI_ATTRIBUTE"):
                for l in v.split(","):
                    post_data.append("X-OCCI-Attribute: %s" % l.strip())
            if k.startswith("HTTP_CATEGORY"):
                for l in v.split(","):
                    post_data.append("Category: %s" % l.strip())
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
        response += "Category: %s\n" % NETWORK_INTERFACE_KIND.render_values()
        response += "Category: %s\n" % (
            IPNETWORK_INTERFACE_MIXIN.render_values())
        for c in COMPUTE_ACTIONS:
            response += "Category: %s\n" % c.render_values()

        templates = InstanceTemplate.get_objects_with_level("user",
                                                            self.request.user)
        for t in templates:
            response += OsTemplate(t).render_body()

        return HttpResponse(
            response,
            content_type="text/plain",
        )

    def post(self, request, *args, **kwargs):
        response = HttpResponse(status=501)
        return response


class ComputeInterface(CSRFExemptMixin, OCCIPostDataAsListMixin, View):

    def get(self, request, *args, **kwargs):
        vms = Instance.get_objects_with_level("user", self.request.user)
        response = "\n".join([Compute(instance=i).render_location()
                             for i in vms])
        return HttpResponse(
            response,
            content_type="text/plain",
        )

    def post(self, request, *args, **kwargs):
        data = self.get_post_data(request)

        c = Compute.create_object(data=data, user=self.request.user)
        response = HttpResponse(
            "X-OCCI-Location: %s" % c.location,
            status=201,
            content_type="text/plain",
        )
        return response


class VmInterface(CSRFExemptMixin, OCCIPostDataAsListMixin, DetailView):
    model = Instance

    def get_object(self):
        vm = get_object_or_404(Instance.objects.filter(destroyed_at=None),
                               pk=self.kwargs['pk'])
        if not vm.has_level(self.request.user, "user"):
            raise PermissionDenied()
        return vm

    def get(self, request, *args, **kwargs):
        vm = self.get_object()
        c = Compute(instance=vm)
        return HttpResponse(
            c.render_body(),
            content_type="text/plain",
        )

    def post(self, request, *args, **kwargs):
        data = self.get_post_data(request)
        action = request.GET.get("action")
        vm = self.get_object()
        if action:
            Compute(instance=vm).trigger_action(data, self.request.user)
        return HttpResponse()

    def delete(self, request, *args, **kwargs):
        vm = self.get_object()
        Compute(instance=vm).delete(self.request.user)

        return HttpResponse()


class OsTplInterface(CSRFExemptMixin, View):

    def get(self, request, *args, **kwargs):
        templates = InstanceTemplate.get_objects_with_level("user",
                                                            self.request.user)
        response = "\n".join([OsTemplate(template=t).render_location()
                             for t in templates])
        return HttpResponse(
            response,
            content_type="text/plain",
        )

    def post(self, request, *args, **kwargs):
        pass


class StorageInterface(CSRFExemptMixin, OCCIPostDataAsListMixin, View):

    def get(self, request, *args, **kwargs):
        response = "\n".join([Storage(disk=d).render_location()
                             for d in Disk.objects.filter(destroyed=None)])
        return HttpResponse(
            response,
            content_type="text/plain",
        )

    def post(self, request, *args, **kwargs):
        data = self.get_post_data(request)

        d = Storage.create_object(data=data, user=self.request.user)
        response = HttpResponse(
            "X-OCCI-Location: %s" % d.location,
            status=201,
            content_type="text/plain",
        )
        return response


class DiskInterface(CSRFExemptMixin, OCCIPostDataAsListMixin, DetailView):
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
        data = self.get_post_data(request)
        action = request.GET.get("action")
        disk = self.get_object()
        if action:
            Storage(disk=disk).trigger_action(data, self.request.user)
        return HttpResponse()

    def delete(self, request, *args, **kwargs):
        Storage(disk=self.get_object()).delete(self.request.user)
        return HttpResponse("")


class StorageLinkInterface(CSRFExemptMixin, OCCIPostDataAsListMixin, View):

    def get_vm_and_disk(self):
        vm = get_object_or_404(Instance.objects.filter(destroyed_at=None),
                               pk=self.kwargs['vm_pk'])
        disk = get_object_or_404(Disk.objects.filter(destroyed=None),
                                 pk=self.kwargs['disk_pk'])

        if disk not in vm.disks.all():
            raise Http404

        if not vm.has_level(self.request.user, "user"):
            raise PermissionDenied()

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

        data = self.get_post_data(request)
        sl = StorageLink.create_object(data=data, user=self.request.user)
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

        sl.delete(user=self.request.user)
        return HttpResponse("")


class NetworkInterfaceView(CSRFExemptMixin, View):

    def get(self, request, *args, **kwargs):
        vlans = Vlan.get_objects_with_level("user", self.request.user)
        response = "\n".join([Network(vlan=v).render_location()
                             for v in vlans])
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

    def get_object(self):
        vlan = get_object_or_404(Vlan, vid=self.kwargs['vid'])
        if not vlan.has_level(self.request.user, "user"):
            raise PermissionDenied()

        return vlan

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
        pass


class CIRCLEInterface(CSRFExemptMixin, OCCIPostDataAsListMixin, View):
    def get_vm_and_vlan(self):
        vlan_vid = self.kwargs['vlan_vid']
        vm = get_object_or_404(Instance.objects.filter(destroyed_at=None),
                               pk=self.kwargs['vm_pk'])
        vlan = get_object_or_404(Vlan, vid=vlan_vid)

        if not vm.has_level(self.request.user, "user"):
            raise PermissionDenied()

        get_object_or_404(Interface, vlan=vlan, instance=vm)

        return vm, vlan

    def get(self, request, *args, **kwargs):
        vm, vlan = self.get_vm_and_vlan()
        ni = NetworkInterface(instance=vm, vlan=vlan)
        return HttpResponse(
            ni.render_as_category(),
            content_type="text/plain",
        )

    def post(self, request, *args, **kwargs):
        # we don't support actions for networkinterfaces
        if request.GET.get("action"):
            return HttpResponse("", status=500)

        data = self.get_post_data(request)
        sl = NetworkInterface.create_object(data=data, user=self.request.user)
        if sl:
            response = HttpResponse(
                "X-OCCI-Location: %s" % sl.location,
                status=201,
                content_type="text/plain",
            )
            return response
        else:
            return HttpResponse("VM or Network does not exist.", status=500)

    def delete(self, request, *args, **kwargs):
        vm, vlan = self.get_vm_and_vlan()
        ni = NetworkInterface(instance=vm, vlan=vlan)

        ni.delete(user=self.request.user)
        return HttpResponse("")
