from __future__ import unicode_literals, absolute_import

from django.views.generic import (
    UpdateView, TemplateView, DetailView, CreateView, FormView,
)
from django.shortcuts import redirect, get_object_or_404
from django.core.exceptions import PermissionDenied

from braces.views import SuperuserRequiredMixin, LoginRequiredMixin
from django_tables2 import SingleTableView

from request.models import (
    Request, TemplateAccessType, LeaseType, TemplateAccessAction,
    ExtendLeaseAction, ResourceChangeAction,
)
from vm.models import Instance
from request.tables import (
    RequestTable, TemplateAccessTypeTable, LeaseTypeTable,
)
from request.forms import (
    LeaseTypeForm, TemplateAccessTypeForm, TemplateRequestForm,
    LeaseRequestForm, ResourceRequestForm,
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


class RequestDetail(LoginRequiredMixin, SuperuserRequiredMixin, DetailView):
    model = Request
    template_name = "request/detail.html"

    def post(self, *args, **kwargs):
        accept = self.request.POST.get("accept")
        request = self.get_object()  # not self.request!
        if accept:
            request.accept()
        else:
            request.decline()

        return redirect(request.get_absolute_url())

    def get_context_data(self, **kwargs):
        request = self.object
        context = super(RequestDetail, self).get_context_data(**kwargs)

        context['action'] = request.action

        if request.status == Request.STATUSES.UNSEEN:
            request.status = Request.STATUSES.PENDING
            request.save()
        return context


class TemplateAccessTypeDetail(LoginRequiredMixin, SuperuserRequiredMixin,
                               UpdateView):
    model = TemplateAccessType
    template_name = "request/template-type-form.html"
    form_class = TemplateAccessTypeForm


class TemplateAccessTypeCreate(LoginRequiredMixin, SuperuserRequiredMixin,
                               CreateView):
    model = TemplateAccessType
    template_name = "request/template-type-form.html"
    form_class = TemplateAccessTypeForm


class LeaseTypeDetail(LoginRequiredMixin, SuperuserRequiredMixin, UpdateView):
    model = LeaseType
    template_name = "request/lease-type-form.html"
    form_class = LeaseTypeForm


class LeaseTypeCreate(LoginRequiredMixin, SuperuserRequiredMixin, CreateView):
    model = LeaseType
    template_name = "request/lease-type-form.html"
    form_class = LeaseTypeForm


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


class TemplateRequestView(FormView):
    form_class = TemplateRequestForm
    template_name = "request/request-template.html"

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
            reason=data['reason'],
            type=Request.TYPES.template,
            action=ta
        )
        req.save()

        return redirect("/")


class LeaseRequestView(FormView):
    form_class = LeaseRequestForm
    template_name = "request/request-lease.html"

    def get_vm(self):
        return get_object_or_404(Instance, pk=self.kwargs['vm_pk'])

    def dispatch(self, *args, **kwargs):
        vm = self.get_vm()
        user = self.request.user
        if not vm.has_level(user, 'operator'):
            raise PermissionDenied()
        return super(LeaseRequestView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(LeaseRequestView, self).get_context_data(**kwargs)
        context['vm'] = self.get_vm()
        return context

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
            reason=data['reason'],
            type=Request.TYPES.lease,
            action=el
        )
        req.save()

        return redirect(vm.get_absolute_url())


class ResourceRequestView(FormView):
    form_class = ResourceRequestForm
    template_name = "request/request-resource.html"

    def get_vm(self):
        return get_object_or_404(Instance, pk=self.kwargs['vm_pk'])

    def dispatch(self, *args, **kwargs):
        vm = self.get_vm()
        user = self.request.user
        if not vm.has_level(user, "user"):
            raise PermissionDenied()
        return super(ResourceRequestView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ResourceRequestView, self).get_context_data(**kwargs)
        context['vm'] = self.get_vm()
        return context

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
            reason=data['reason'],
            type=Request.TYPES.resource,
            action=rc
        )
        req.save()

        return redirect(vm.get_absolute_url())
