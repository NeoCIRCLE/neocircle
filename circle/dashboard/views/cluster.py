from __future__ import unicode_literals, absolute_import

import json

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponse
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.views.generic import DetailView, TemplateView, UpdateView
from braces.views import LoginRequiredMixin, SuperuserRequiredMixin
from django_tables2 import SingleTableView

from vm.models import Node, Trait
from ..forms import TraitForm, ClusterCreateForm
from ..tables import ClusterListTable
from .util import GraphMixin, DeleteViewBase
from vm.models.cluster import Cluster

import django_tables2 as tables
from django_tables2.columns import TemplateColumn


class UnmanagedVmsTable(tables.Table):
    name = tables.Column(orderable=False, verbose_name="Name")
    state = tables.Column(orderable=False, verbose_name="Current power state")
    os = tables.Column(orderable=False, verbose_name='Operating system')
    memory = TemplateColumn("{{ value }} MB", orderable=False, verbose_name='Memory')
    cpu = tables.Column(orderable=False, verbose_name='CPU cores')
    add_btn = TemplateColumn(orderable=False, template_name="dashboard/vmwarevminstance-list/column-add.html",
                             verbose_name="Actions")

    class Meta:
        attrs = {'class': 'table table-bordered table-striped table-hover'}


class ManagedVmsTable(tables.Table):
    name = tables.Column(orderable=False, verbose_name="Name")
    time_of_expiration = tables.Column(orderable=False, verbose_name="Expiration time")
    state = tables.Column(orderable=False, verbose_name="Current power state")
    os = tables.Column(orderable=False, verbose_name='Operating system')
    owner = tables.Column(orderable=False, verbose_name='Owner')
    memory = TemplateColumn("{{ value }} MB", orderable=False, verbose_name='Memory')
    cpu = tables.Column(orderable=False, verbose_name='# of CPU cores')
    add_btn = TemplateColumn(orderable=False, template_name="dashboard/vmwarevminstance-list/column-modify.html",
                             verbose_name="Actions")

    class Meta:
        attrs = {'class': 'table table-bordered table-striped table-hover'}


class DeletedVmsTable(tables.Table):
    name = tables.Column(orderable=False, verbose_name="Name")
    os = tables.Column(orderable=False, verbose_name='Operating system')
    memory = TemplateColumn("{{ value }} MB", orderable=False, verbose_name='Memory')
    cpu = tables.Column(orderable=False, verbose_name='# of CPU cores')
    owner = tables.Column(orderable=False, verbose_name='Owner')
    remove_btn = TemplateColumn(orderable=False, template_name="dashboard/vmwarevminstance-list/column-remove.html",
                                verbose_name="Actions")

    class Meta:
        attrs = {'class': 'table table-bordered table-striped table-hover'}


class ClusterDetailView(LoginRequiredMixin, DetailView):
    template_name = "dashboard/cluster-detail.html"
    model = Cluster

    def get(self, *args, **kwargs):
        if not self.request.user.has_perm('vm.view_statistics'):
            raise PermissionDenied()
        return super(ClusterDetailView, self).get(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ClusterDetailView, self).get_context_data(**kwargs)
        unmanaged_vms, managed_vms, deleted_vms, error_msg = self.object.get_list_of_vms()

        if error_msg is not None:
            messages.error(self.request, error_msg)
        else:
            unmanaged_vms_table = UnmanagedVmsTable(unmanaged_vms)
            managed_vms_table = ManagedVmsTable(managed_vms)
            deleted_vms_table = DeletedVmsTable(deleted_vms)

            context.update({
                'unmanaged_vms_table': unmanaged_vms_table,
                'managed_vms_table': managed_vms_table,
                'deleted_vms_table': deleted_vms_table,
            })

        return context

    def post(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied()
        if request.POST.get('new_name'):
            return self.__set_name(request)
        if request.POST.get('to_remove'):
            return self.__remove_trait(request)
        return redirect(reverse_lazy("dashboard.views.cluster-detail",
                                     kwargs={'pk': self.get_object().pk}))

    def __set_name(self, request):
        self.object = self.get_object()
        new_name = request.POST.get("new_name")
        Cluster.objects.filter(pk=self.object.pk).update(
            **{'name': new_name})

        success_message = _("Cluster successfully renamed.")
        if request.is_ajax():
            response = {
                'message': success_message,
                'new_name': new_name,
                'node_pk': self.object.pk
            }
            return HttpResponse(
                json.dumps(response),
                content_type="application/json"
            )
        else:
            messages.success(request, success_message)
            return redirect(reverse_lazy("dashboard.views.cluster-detail",
                                         kwargs={'pk': self.object.pk}))


class ClusterList(LoginRequiredMixin, GraphMixin, SingleTableView):
    template_name = "dashboard/cluster-list.html"
    table_class = ClusterListTable
    table_pagination = False

    def get(self, *args, **kwargs):
        if not self.request.user.has_perm('vm.view_statistics'):
            raise PermissionDenied()
        if self.request.is_ajax():
            nodes = Node.objects.all()
            nodes = [{
                'name': i.name,
                'icon': i.get_status_icon(),
                'url': i.get_absolute_url(),
                'label': i.get_status_label(),
                'status': i.state.lower()} for i in nodes]

            return HttpResponse(
                json.dumps(list(nodes)),
                content_type="application/json",
            )
        else:
            return super(ClusterList, self).get(*args, **kwargs)

    def get_queryset(self):
        return Cluster.objects.all()


class ClusterCreate(LoginRequiredMixin, TemplateView):

    model = Cluster
    form_class = ClusterCreateForm
    template_name = 'dashboard/cluster-create.html'

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/_modal.html']
        else:
            return ['dashboard/nojs-wrapper.html']

    def get(self, request, form=None, *args, **kwargs):
        if not request.user.has_module_perms('auth'):
            raise PermissionDenied()
        if form is None:
            form = self.form_class()
        context = self.get_context_data(**kwargs)
        context.update({
            'template': 'dashboard/cluster-create.html',
            'box_title': _('Add a Cluster'),
            'form': form,
            'ajax_title': True,
        })
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        if not request.user.has_module_perms('auth'):
            raise PermissionDenied()
        form = self.form_class(request.POST)
        if not form.is_valid():
            return self.get(request, form, *args, **kwargs)
        form.cleaned_data
        savedform = form.save()
        messages.success(request, _('Cluster successfully created.'))
        if request.is_ajax():
            return HttpResponse(json.dumps({'redirect':
                                reverse("dashboard.index")}),
                                content_type="application/json")
        else:
            return redirect(reverse("dashboard.index"))


class ClusterEdit(SuperuserRequiredMixin, UpdateView):
    model = Cluster
    success_message = _("Cluster successfully updated.")
    template_name = 'dashboard/cluster-edit.html'
    form_class = ClusterCreateForm

    def check_auth(self):
        # SuperuserRequiredMixin
        pass

    def get_success_url(self):
        return reverse_lazy('dashboard.index')

    def get_context_data(self, **kwargs):
        context = super(ClusterEdit, self).get_context_data(**kwargs)
        context['cluster'] = self.object

        return context


class ClusterDelete(SuperuserRequiredMixin, DeleteViewBase):
    model = Cluster
    success_message = _("Cluster successfully deleted.")

    def check_auth(self):
        # SuperuserRequiredMixin
        pass

    def get_success_url(self):
        return reverse_lazy('dashboard.index')
