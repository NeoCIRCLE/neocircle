# Copyright 2014 Budapest University of Technology and Economics (BME IK)
#
# This file is part of CIRCLE Cloud.
#
# CIRCLE is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# CIRCLE is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along
# with CIRCLE.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import unicode_literals, absolute_import

from django.views.generic import (
    UpdateView, TemplateView, DetailView, CreateView, FormView, DeleteView,
)
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect, get_object_or_404
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.http import JsonResponse

from braces.views import SuperuserRequiredMixin, LoginRequiredMixin
from django_tables2 import SingleTableView

from request.models import (
    Request, TemplateAccessType, LeaseType, TemplateAccessAction,
    ExtendLeaseAction, ResourceChangeAction, DiskResizeAction
)
from storage.models import Disk
from vm.models import Instance
from request.tables import (
    RequestTable, TemplateAccessTypeTable, LeaseTypeTable,
)
from request.forms import (
    LeaseTypeForm, TemplateAccessTypeForm, TemplateRequestForm,
    LeaseRequestForm, ResourceRequestForm, ResizeRequestForm,
)


class RequestList(LoginRequiredMixin, SuperuserRequiredMixin, SingleTableView):
    model = Request
    table_class = RequestTable
    template_name = "request/list.html"

    def get_context_data(self, **kwargs):
        context = super(RequestList, self).get_context_data(**kwargs)
        context['statuses'] = Request.STATUSES
        return context

    def get_table_data(self):
        data = Request.objects.all()
        status = self.request.GET.get("status")
        if status:
            data = data.filter(status=status)

        return data


class RequestDetail(LoginRequiredMixin, DetailView):
    model = Request
    template_name = "request/detail.html"

    def post(self, *args, **kwargs):
        user = self.request.user
        request = self.get_object()  # not self.request!

        if not user.is_superuser:
            raise SuspiciousOperation

        if self.get_object().status == "PENDING":
            accept = self.request.POST.get("accept")
            reason = self.request.POST.get("reason")
            if accept:
                request.accept(user)
            else:
                request.decline(user, reason)

        return redirect(request.get_absolute_url())

    def get_context_data(self, **kwargs):
        request = self.object
        user = self.request.user

        if not user.is_superuser and request.user != user:
            raise SuspiciousOperation

        context = super(RequestDetail, self).get_context_data(**kwargs)

        context['action'] = request.action
        context['is_acceptable'] = request.is_acceptable
        # workaround for http://git.io/vIIYi
        context['request'] = self.request

        return context


class TemplateAccessTypeDetail(LoginRequiredMixin, SuperuserRequiredMixin,
                               SuccessMessageMixin, UpdateView):
    model = TemplateAccessType
    template_name = "request/template-type-form.html"
    form_class = TemplateAccessTypeForm
    success_message = _("Template access type successfully updated.")


class TemplateAccessTypeCreate(LoginRequiredMixin, SuperuserRequiredMixin,
                               SuccessMessageMixin, CreateView):
    model = TemplateAccessType
    template_name = "request/template-type-form.html"
    form_class = TemplateAccessTypeForm
    success_message = _("New template access type successfully created.")


class TemplateAccessTypeDelete(LoginRequiredMixin, SuperuserRequiredMixin,
                               DeleteView):
    model = TemplateAccessType
    template_name = "dashboard/confirm/base-delete.html"

    def get_success_url(self):
        return reverse("request.views.type-list")


class LeaseTypeDetail(LoginRequiredMixin, SuperuserRequiredMixin,
                      SuccessMessageMixin, UpdateView):
    model = LeaseType
    template_name = "request/lease-type-form.html"
    form_class = LeaseTypeForm
    success_message = _("Lease type successfully updated.")


class LeaseTypeCreate(LoginRequiredMixin, SuperuserRequiredMixin,
                      SuccessMessageMixin, CreateView):
    model = LeaseType
    template_name = "request/lease-type-form.html"
    form_class = LeaseTypeForm
    success_message = _("New lease type successfully created.")


class LeaseTypeDelete(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = LeaseType
    template_name = "dashboard/confirm/base-delete.html"

    def get_success_url(self):
        return reverse("request.views.type-list")


class RequestTypeList(LoginRequiredMixin, SuperuserRequiredMixin,
                      TemplateView):
    template_name = "request/type-list.html"

    def get_context_data(self, **kwargs):
        context = super(RequestTypeList, self).get_context_data(**kwargs)

        context['lease_table'] = LeaseTypeTable(
            LeaseType.objects.all(), request=self.request)
        context['template_table'] = TemplateAccessTypeTable(
            TemplateAccessType.objects.all(), request=self.request)

        return context


class TemplateRequestView(LoginRequiredMixin, FormView):
    form_class = TemplateRequestForm
    template_name = "request/request-template.html"
    success_message = _("Request successfully sent.")

    def get_form_kwargs(self):
        kwargs = super(TemplateRequestView, self).get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        data = form.cleaned_data
        user = self.request.user

        ta = TemplateAccessAction(
            template_type=data['template'],
            level=data['level'],
            user=user,
        )
        ta.save()

        req = Request(
            user=user,
            message=data['message'],
            type=Request.TYPES.template,
            action=ta
        )
        req.save()

        messages.success(self.request, self.success_message)
        return redirect(reverse("dashboard.index"))


class VmRequestMixin(LoginRequiredMixin, object):
    def get_vm(self):
        return get_object_or_404(Instance, pk=self.kwargs['vm_pk'])

    def dispatch(self, *args, **kwargs):
        vm = self.get_vm()
        user = self.request.user
        if not vm.has_level(user, self.user_level):
            raise PermissionDenied()
        return super(VmRequestMixin, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(VmRequestMixin, self).get_context_data(**kwargs)
        context['vm'] = self.get_vm()
        return context

    def get_form_kwargs(self):
        kwargs = super(VmRequestMixin, self).get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        raise NotImplementedError


class LeaseRequestView(VmRequestMixin, FormView):
    form_class = LeaseRequestForm
    template_name = "request/request-lease.html"
    user_level = "operator"
    success_message = _("Request successfully sent.")

    def form_valid(self, form):
        data = form.cleaned_data
        user = self.request.user
        vm = self.get_vm()

        el = ExtendLeaseAction(
            lease_type=data['lease'],
            instance=vm,
        )
        el.save()

        req = Request(
            user=user,
            message=data['message'],
            type=Request.TYPES.lease,
            action=el
        )
        req.save()

        messages.success(self.request, self.success_message)
        return redirect(vm.get_absolute_url())


class ResourceRequestView(VmRequestMixin, FormView):
    form_class = ResourceRequestForm
    template_name = "request/request-resource.html"
    user_level = "user"
    success_message = _("Request successfully sent.")

    def get_form_kwargs(self):
        kwargs = super(ResourceRequestView, self).get_form_kwargs()
        kwargs['can_edit'] = True
        kwargs['instance'] = self.get_vm()
        return kwargs

    def get_initial(self):
        vm = self.get_vm()
        initial = super(ResourceRequestView, self).get_initial()
        initial['num_cores'] = vm.num_cores
        initial['priority'] = vm.priority
        initial['ram_size'] = vm.ram_size
        return initial

    def form_valid(self, form):
        vm = self.get_vm()
        data = form.cleaned_data
        user = self.request.user

        rc = ResourceChangeAction(
            instance=vm,
            num_cores=data['num_cores'],
            priority=data['priority'],
            ram_size=data['ram_size'],
        )
        rc.save()

        req = Request(
            user=user,
            message=data['message'],
            type=Request.TYPES.resource,
            action=rc
        )
        req.save()

        messages.success(self.request, self.success_message)
        return redirect(vm.get_absolute_url())


class ResizeRequestView(VmRequestMixin, FormView):
    form_class = ResizeRequestForm
    template_name = "request/_request-resize-form.html"
    user_level = "owner"
    success_message = _("Request successfully sent.")

    def get_disk(self, *args, **kwargs):
        disk = get_object_or_404(Disk, pk=self.kwargs['disk_pk'])
        if disk not in self.get_vm().disks.all():
            raise SuspiciousOperation
        return disk

    def get_form_kwargs(self):
        kwargs = super(ResizeRequestView, self).get_form_kwargs()
        kwargs['disk'] = self.get_disk()
        return kwargs

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/_modal.html']
        else:
            return ['dashboard/_base.html']

    def get_context_data(self, **kwargs):
        context = super(ResizeRequestView, self).get_context_data(**kwargs)
        context['disk'] = self.get_disk()
        context['template'] = self.template_name
        context['box_title'] = context['title'] = _("Disk resize request")
        context['ajax_title'] = True
        return context

    def form_valid(self, form):
        disk = self.get_disk()
        if not disk.is_resizable:
            raise SuspiciousOperation

        vm = self.get_vm()
        data = form.cleaned_data
        user = self.request.user

        dra = DiskResizeAction(instance=vm, disk=disk, size=data['size'])
        dra.save()

        req = Request(user=user, message=data['message'], action=dra,
                      type=Request.TYPES.resize)
        req.save()

        if self.request.is_ajax():
            return JsonResponse({'success': True,
                                 'messages': [self.success_message]})
        else:
            messages.success(self.request, self.success_message)
            return redirect(vm.get_absolute_url())
