from __future__ import unicode_literals, absolute_import

import json

from braces.views import LoginRequiredMixin, SuperuserRequiredMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView, DetailView
from dashboard.views import DeleteViewBase
from vm.models import VMwareVMInstance
from vm.models.cluster import Cluster
from ..forms import VMwareVMInstanceForm, VMwareVMInstanceCreateForm


class VMwareVMInstanceCreate(LoginRequiredMixin, TemplateView):

    model = VMwareVMInstance
    form_class = VMwareVMInstanceCreateForm
    template_name = 'dashboard/create-vmware-vm.html'

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/_modal.html']
        else:
            return ['dashboard/nojs-wrapper.html']

    def get(self, request, form=None, *args, **kwargs):
        cluster = None

        if 'cluster' in kwargs:
            cluster = kwargs.pop("cluster")

        if not request.user.has_module_perms('auth'):
            raise PermissionDenied()
        if form is None:
            form = self.form_class()
        context = self.get_context_data(**kwargs)
        context.update({
            'template': 'dashboard/create-vmware-vm.html',
            'box_title': _('Create a VMware virtual machine'),
            'form': form,
            'ajax_title': True,
            'cluster_pk': cluster,
        })
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        if not request.user.has_module_perms('auth'):
            raise PermissionDenied()

        cluster = None

        if 'cluster' in kwargs:
            cluster = kwargs.pop("cluster")

        form = self.form_class(request.POST, cluster_pk=int(cluster))
        if not form.is_valid():
            return self.get(request, form, *args, **kwargs)

        savedform = form.save()
        messages.success(request, _('Virtual machine successfully created.'))
        if request.is_ajax():
            return HttpResponse(json.dumps({'redirect':
                                reverse("dashboard.index")}),
                                content_type="application/json")
        else:
            return redirect(reverse("dashboard.index"))


class VMwareVMInstanceAdd(LoginRequiredMixin, TemplateView):

    model = VMwareVMInstance
    form_class = VMwareVMInstanceForm
    template_name = 'dashboard/vmwarevminstance-add.html'

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/_modal.html']
        else:
            return ['dashboard/nojs-wrapper.html']

    def get(self, request, form=None, *args, **kwargs):
        if not request.user.has_module_perms('auth'):
            raise PermissionDenied()

        uuid = None
        cluster = None

        if 'uuid' in kwargs:
            uuid = kwargs.pop("uuid")

        if 'cluster' in kwargs:
            cluster = kwargs.pop("cluster")

        cluster_instance = Cluster.objects.get(pk=cluster)
        vm_info = cluster_instance.get_vm_details_by_uuid(uuid)

        if form is None:
            form = self.form_class(uuid=uuid)
        context = self.get_context_data(**kwargs)
        context.update({
            'template': 'dashboard/vmwarevminstance-add.html',
            'box_title': _('Add a virtual machine: '+vm_info["name"]),
            'form': form,
            'ajax_title': True,
            'instance_uuid': uuid,
            'cluster_pk': cluster,
        })
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        if not request.user.has_module_perms('auth'):
            raise PermissionDenied()

        if 'cluster' in kwargs:
            cluster = kwargs.pop("cluster")

        if 'uuid' in kwargs:
            uuid = kwargs.pop("uuid")

        form = self.form_class(request.POST, cluster_pk=int(cluster), uuid=uuid)
        if not form.is_valid():
            return self.get(request, form, *args, **kwargs)
        form.cleaned_data
        savedform = form.save()
        messages.success(request, _('Virtual machine successfully added.'))
        if request.is_ajax():
            return HttpResponse(json.dumps({'redirect':
                                reverse("dashboard.index")}),
                                content_type="application/json")
        else:
            return redirect(reverse("dashboard.index"))


class VMwareVMInstanceDelete(SuperuserRequiredMixin, DeleteViewBase):
    model = VMwareVMInstance
    success_message = _("Instance has been successfully deleted.")

    def check_auth(self):
        # SuperuserRequiredMixin
        pass

    def get_success_url(self):
        return reverse_lazy('dashboard.index')


class VMwareVMInstanceDetail(LoginRequiredMixin, DetailView):
    template_name = "dashboard/vmware-vm-instance-detail.html"
    model = VMwareVMInstance

    def get(self, *args, **kwargs):
        if not self.request.user.has_perm('vm.view_statistics'):
            raise PermissionDenied()
        return super(VMwareVMInstanceDetail, self).get(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(VMwareVMInstanceDetail, self).get_context_data(**kwargs)
        context['instance'] = self.object
        vm_info = self.object.get_vm_info()

        context['vm_info'] = vm_info
        context['status_icon'] = self.object.get_status_icon(vm_info['state'])

        return context