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
    # ExtendLeaseAction,
)
from vm.models import Instance
from request.tables import (
    RequestTable, TemplateAccessTypeTable, LeaseTypeTable,
)
from request.forms import (
    LeaseTypeForm, TemplateAccessTypeForm, TemplateRequestForm,
    LeaseRequestForm,
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

    def get_context_data(self, **kwargs):
        vm = get_object_or_404(Instance, pk=self.kwargs['vm_pk'])
        user = self.request.user
        if not vm.has_level(user, 'operator'):
            raise PermissionDenied()

        context = super(LeaseRequestView, self).get_context_data(**kwargs)
        context['vm'] = vm
        return context

    def form_valid(self, form):
        pass
