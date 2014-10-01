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

import json
import logging

from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.messages.views import SuccessMessageMixin
from django.core.urlresolvers import reverse, reverse_lazy
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, get_object_or_404
from django.utils.translation import ugettext as _
from django.views.generic import (
    TemplateView, CreateView, DeleteView, UpdateView,
)

from braces.views import (
    LoginRequiredMixin, PermissionRequiredMixin, SuperuserRequiredMixin,
)
from django_tables2 import SingleTableView

from vm.models import InstanceTemplate, InterfaceTemplate, Instance, Lease
from storage.models import Disk

from ..forms import (
    TemplateForm, TemplateListSearchForm, AclUserOrGroupAddForm, LeaseForm,
)
from ..tables import TemplateListTable, LeaseListTable

from .util import AclUpdateView, FilterMixin

logger = logging.getLogger(__name__)


class TemplateChoose(LoginRequiredMixin, TemplateView):

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/modal-wrapper.html']
        else:
            return ['dashboard/nojs-wrapper.html']

    def get_context_data(self, *args, **kwargs):
        context = super(TemplateChoose, self).get_context_data(*args, **kwargs)
        templates = InstanceTemplate.get_objects_with_level("user",
                                                            self.request.user)
        context.update({
            'box_title': _('Choose template'),
            'ajax_title': True,
            'template': "dashboard/_template-choose.html",
            'templates': templates.all(),
        })
        return context

    def post(self, request, *args, **kwargs):
        if not request.user.has_perm('vm.create_template'):
            raise PermissionDenied()

        template = request.POST.get("parent")
        if template == "base_vm":
            return redirect(reverse("dashboard.views.template-create"))
        elif template is None:
            messages.warning(request, _("Select an option to proceed."))
            return redirect(reverse("dashboard.views.template-choose"))
        else:
            template = get_object_or_404(InstanceTemplate, pk=template)

        if not template.has_level(request.user, "user"):
            raise PermissionDenied()

        instance = Instance.create_from_template(
            template=template, owner=request.user, is_base=True)

        return redirect(instance.get_absolute_url())


class TemplateCreate(SuccessMessageMixin, CreateView):
    model = InstanceTemplate
    form_class = TemplateForm

    def get_template_names(self):
        if self.request.is_ajax():
            pass
        else:
            return ['dashboard/nojs-wrapper.html']

    def get_context_data(self, *args, **kwargs):
        context = super(TemplateCreate, self).get_context_data(*args, **kwargs)

        num_leases = Lease.get_objects_with_level("operator",
                                                  self.request.user).count()
        can_create_leases = self.request.user.has_perm("create_leases")
        context.update({
            'box_title': _("Create a new base VM"),
            'template': "dashboard/_template-create.html",
            'show_lease_create': num_leases < 1 and can_create_leases
        })
        return context

    def get(self, *args, **kwargs):
        if not self.request.user.has_perm('vm.create_base_template'):
            raise PermissionDenied()

        return super(TemplateCreate, self).get(*args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(TemplateCreate, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def post(self, request, *args, **kwargs):
        if not self.request.user.has_perm('vm.create_base_template'):
            raise PermissionDenied()

        form = self.form_class(request.POST, user=request.user)
        if not form.is_valid():
            return self.get(request, form, *args, **kwargs)
        else:
            post = form.cleaned_data
            networks = self.__create_networks(post.pop("networks"),
                                              request.user)
            post.pop("parent")
            post['max_ram_size'] = post['ram_size']
            req_traits = post.pop("req_traits")
            tags = post.pop("tags")
            post['pw'] = User.objects.make_random_password()
            post['is_base'] = True
            inst = Instance.create(params=post, disks=[],
                                   networks=networks,
                                   tags=tags, req_traits=req_traits)

            return HttpResponseRedirect("%s#resources" %
                                        inst.get_absolute_url())

    def __create_networks(self, vlans, user):
        networks = []
        for v in vlans:
            if not v.has_level(user, "user"):
                raise PermissionDenied()
            networks.append(InterfaceTemplate(vlan=v, managed=v.managed))
        return networks

    def get_success_url(self):
        return reverse_lazy("dashboard.views.template-list")


class TemplateAclUpdateView(AclUpdateView):
    model = InstanceTemplate


class TemplateList(LoginRequiredMixin, FilterMixin, SingleTableView):
    template_name = "dashboard/template-list.html"
    model = InstanceTemplate
    table_class = TemplateListTable
    table_pagination = False

    allowed_filters = {
        'name': "name__icontains",
        'tags[]': "tags__name__in",
        'tags': "tags__name__in",  # for search string
        'owner': "owner__username",
        'ram': "ram_size",
        'ram_size': "ram_size",
        'cores': "num_cores",
        'num_cores': "num_cores",
        'access_method': "access_method__iexact",
    }

    def get_context_data(self, *args, **kwargs):
        context = super(TemplateList, self).get_context_data(*args, **kwargs)
        user = self.request.user
        leases_w_operator = Lease.get_objects_with_level("operator", user)
        context['lease_table'] = LeaseListTable(
            leases_w_operator, request=self.request,
            template="django_tables2/table_no_page.html",
        )
        context['show_lease_table'] = (
            leases_w_operator.count() > 0 or
            user.has_perm("vm.create_leases")
        )

        context['search_form'] = self.search_form

        return context

    def get(self, *args, **kwargs):
        self.search_form = TemplateListSearchForm(self.request.GET)
        self.search_form.full_clean()
        return super(TemplateList, self).get(*args, **kwargs)

    def create_acl_queryset(self, model):
        queryset = super(TemplateList, self).create_acl_queryset(model)
        sql = ("SELECT count(*) FROM vm_instance WHERE "
               "vm_instance.template_id = vm_instancetemplate.id and "
               "vm_instance.destroyed_at is null and "
               "vm_instance.status = 'RUNNING'")
        queryset = queryset.extra(select={'running': sql})
        return queryset

    def get_queryset(self):
        logger.debug('TemplateList.get_queryset() called. User: %s',
                     unicode(self.request.user))
        qs = self.create_acl_queryset(InstanceTemplate)
        self.create_fake_get()

        try:
            qs = qs.filter(**self.get_queryset_filters()).distinct()
        except ValueError:
            messages.error(self.request, _("Error during filtering."))

        return qs.select_related("lease", "owner", "owner__profile")


class TemplateDelete(LoginRequiredMixin, DeleteView):
    model = InstanceTemplate

    def get_success_url(self):
        return reverse("dashboard.views.template-list")

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/confirm/ajax-delete.html']
        else:
            return ['dashboard/confirm/base-delete.html']

    def delete(self, request, *args, **kwargs):
        object = self.get_object()
        if not object.has_level(request.user, 'owner'):
            raise PermissionDenied()

        object.destroy_disks()
        object.delete()
        success_url = self.get_success_url()
        success_message = _("Template successfully deleted.")

        if request.is_ajax():
            return HttpResponse(
                json.dumps({'message': success_message}),
                content_type="application/json",
            )
        else:
            messages.success(request, success_message)
            return HttpResponseRedirect(success_url)


class TemplateDetail(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = InstanceTemplate
    template_name = "dashboard/template-edit.html"
    form_class = TemplateForm
    success_message = _("Successfully modified template.")

    def get(self, request, *args, **kwargs):
        template = self.get_object()
        if not template.has_level(request.user, 'user'):
            raise PermissionDenied()
        if request.is_ajax():
            template = {
                'num_cores': template.num_cores,
                'ram_size': template.ram_size,
                'priority': template.priority,
                'arch': template.arch,
                'description': template.description,
                'system': template.system,
                'name': template.name,
                'disks': [{'pk': d.pk, 'name': d.name}
                          for d in template.disks.all()],
                'network': [
                    {'vlan_pk': i.vlan.pk, 'vlan': i.vlan.name,
                     'managed': i.managed}
                    for i in InterfaceTemplate.objects.filter(
                        template=self.get_object()).all()
                ]
            }
            return HttpResponse(json.dumps(template),
                                content_type="application/json")
        else:
            return super(TemplateDetail, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        obj = self.get_object()
        context = super(TemplateDetail, self).get_context_data(**kwargs)
        context['acl'] = AclUpdateView.get_acl_data(
            obj, self.request.user, 'dashboard.views.template-acl')
        context['disks'] = obj.disks.all()
        context['is_owner'] = obj.has_level(self.request.user, 'owner')
        context['aclform'] = AclUserOrGroupAddForm()
        context['parent'] = obj.parent
        return context

    def get_success_url(self):
        return reverse_lazy("dashboard.views.template-detail",
                            kwargs=self.kwargs)

    def post(self, request, *args, **kwargs):
        template = self.get_object()
        if not template.has_level(request.user, 'owner'):
            raise PermissionDenied()
        return super(TemplateDetail, self).post(self, request, args, kwargs)

    def get_form_kwargs(self):
        kwargs = super(TemplateDetail, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class DiskRemoveView(DeleteView):
    model = Disk

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/confirm/ajax-delete.html']
        else:
            return ['dashboard/confirm/base-delete.html']

    def get_context_data(self, **kwargs):
        context = super(DiskRemoveView, self).get_context_data(**kwargs)
        disk = self.get_object()
        app = disk.get_appliance()
        context['title'] = _("Disk remove confirmation")
        context['text'] = _("Are you sure you want to remove "
                            "<strong>%(disk)s</strong> from "
                            "<strong>%(app)s</strong>?" % {'disk': disk,
                                                           'app': app}
                            )
        return context

    def delete(self, request, *args, **kwargs):
        disk = self.get_object()
        app = disk.get_appliance()

        if not app.has_level(request.user, 'owner'):
            raise PermissionDenied()

        app.remove_disk(disk=disk, user=request.user)
        disk.destroy()

        next_url = request.POST.get("next")
        success_url = next_url if next_url else app.get_absolute_url()
        success_message = _("Disk successfully removed.")

        if request.is_ajax():
            return HttpResponse(
                json.dumps({'message': success_message}),
                content_type="application/json",
            )
        else:
            messages.success(request, success_message)
            return HttpResponseRedirect("%s#resources" % success_url)


class LeaseCreate(LoginRequiredMixin, PermissionRequiredMixin,
                  SuccessMessageMixin, CreateView):
    model = Lease
    form_class = LeaseForm
    permission_required = 'vm.create_leases'
    template_name = "dashboard/lease-create.html"
    success_message = _("Successfully created a new lease.")

    def get_success_url(self):
        return reverse_lazy("dashboard.views.template-list")


class LeaseAclUpdateView(AclUpdateView):
    model = Lease


class LeaseDetail(LoginRequiredMixin, SuperuserRequiredMixin,
                  SuccessMessageMixin, UpdateView):
    model = Lease
    form_class = LeaseForm
    template_name = "dashboard/lease-edit.html"
    success_message = _("Successfully modified lease.")

    def get_context_data(self, *args, **kwargs):
        obj = self.get_object()
        context = super(LeaseDetail, self).get_context_data(*args, **kwargs)
        context['acl'] = AclUpdateView.get_acl_data(
            obj, self.request.user, 'dashboard.views.lease-acl')
        return context

    def get_success_url(self):
        return reverse_lazy("dashboard.views.lease-detail", kwargs=self.kwargs)


class LeaseDelete(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = Lease

    def get_success_url(self):
        return reverse("dashboard.views.template-list")

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/confirm/ajax-delete.html']
        else:
            return ['dashboard/confirm/base-delete.html']

    def get_context_data(self, *args, **kwargs):
        c = super(LeaseDelete, self).get_context_data(*args, **kwargs)
        lease = self.get_object()
        templates = lease.instancetemplate_set
        if templates.count() > 0:
            text = _("You can't delete this lease because some templates "
                     "are still using it, modify these to proceed: ")

            c['text'] = text + ", ".join("<strong>%s (#%d)</strong>"
                                         "" % (o.name, o.pk)
                                         for o in templates.all())
            c['disable_submit'] = True
        return c

    def delete(self, request, *args, **kwargs):
        object = self.get_object()

        if (object.instancetemplate_set.count() > 0):
            raise SuspiciousOperation()

        object.delete()
        success_url = self.get_success_url()
        success_message = _("Lease successfully deleted.")

        if request.is_ajax():
            return HttpResponse(
                json.dumps({'message': success_message}),
                content_type="application/json",
            )
        else:
            messages.success(request, success_message)
            return HttpResponseRedirect(success_url)
