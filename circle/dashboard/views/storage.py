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

import logging

from django.contrib import messages
from django.core.urlresolvers import reverse, reverse_lazy
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _, ugettext
from django.views.generic import (
    UpdateView, TemplateView, CreateView, DeleteView
)
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django_tables2 import SingleTableView
from django.http import (
    Http404, HttpResponse, HttpResponseRedirect, JsonResponse
)
from django.core.exceptions import PermissionDenied

from braces.views import SuperuserRequiredMixin
from sizefield.utils import filesizeformat

from common.models import WorkerNotFound
from storage.models import DataStore, Disk, Endpoint
from ..tables import DiskListTable, StorageListTable, EndpointListTable
from ..forms import (
    DataStoreForm, CephDataStoreForm, DiskForm, StorageListSearchForm,
    EndpointForm, EndpointListSearchForm
)
from .util import FilterMixin
import json
from celery.exceptions import TimeoutError

logger = logging.getLogger(__name__)


class StorageChoose(SuperuserRequiredMixin, TemplateView):

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/_modal.html']
        else:
            return ['dashboard/nojs-wrapper.html']

    def get_context_data(self, *args, **kwargs):
        context = super(StorageChoose, self).get_context_data(*args, **kwargs)
        types = DataStore.TYPES
        context.update({
            'box_title': _('Choose data store type'),
            'ajax_title': True,
            'template': "dashboard/_storage-choose.html",
            'types': types,
        })
        return context

    def post(self, request, *args, **kwargs):
        if not request.user.has_perm('storage.add_datastore'):
            raise PermissionDenied()

        type = request.POST.get("type")
        if any(type in t for t in DataStore.TYPES):
            return redirect(reverse("dashboard.views.storage-create",
                                    kwargs={"type": type}))
        else:
            messages.warning(request, _("Select an option to proceed."))
            return redirect(reverse("dashboard.views.storage-choose"))


class StorageCreate(SuccessMessageMixin, CreateView):
    model = DataStore
    form = None

    def get_template_names(self):
        if self.request.is_ajax():
            pass
        else:
            return ['dashboard/nojs-wrapper.html']

    def get_context_data(self, *args, **kwargs):
        context = super(StorageCreate, self).get_context_data(*args, **kwargs)
        context.update({
            'box_title': _("Create a new data store"),
            'template': "dashboard/_storage-create.html",
        })
        return context

    def get(self, *args, **kwargs):
        if not self.request.user.has_perm('storage.add_datastore'):
            raise PermissionDenied()

        return super(StorageCreate, self).get(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not self.request.user.has_perm('storage.add_datastore'):
            raise PermissionDenied()

        self.form = self.form_class(request.POST)
        if not self.form.is_valid():
            logger.debug("invalid form")
            return self.get(request, self.form, *args, **kwargs)
        else:
            self.form.save()
            return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy("dashboard.views.storage-list")

    def get_form(self):

        if self.form is not None:
            return self.form
        else:
            type = self.kwargs.get("type")
            fc = self.form_class
            f = fc(initial={"type": type})
            return f

    @property
    def form_class(self):
        type = self.kwargs.get("type")
        if type == "file":
            fc = DataStoreForm
        elif type == "ceph_block":
            fc = CephDataStoreForm
        else:
            raise Http404(_("Invalid creation type"))
        return fc


class StorageList(SuperuserRequiredMixin, FilterMixin, SingleTableView):
    template_name = "dashboard/storage-list.html"
    model = DataStore
    table_class = StorageListTable
    table_pagination = False

    allowed_filters = {
        'name': "name__icontains",
        'type': "type__icontains",
        'path': "path__icontains",
        'poolname': "path__icontains",
        'hostname': "hostname__iexact",
        'address': "endpoints__address__in"
    }

    def get_context_data(self, *args, **kwargs):
        context = super(StorageList, self).get_context_data(*args, **kwargs)
        context['search_form'] = self.search_form
        return context

    def get(self, *args, **kwargs):
        self.search_form = StorageListSearchForm(self.request.GET)
        self.search_form.full_clean()

        return super(StorageList, self).get(*args, **kwargs)

    def get_queryset(self):
        logger.debug('StorageList.get_queryset() called. User: %s',
                     unicode(self.request.user))
        qs = DataStore.get_all()
        self.create_fake_get()

        try:
            filters, excludes = self.get_queryset_filters()
            qs = qs.filter(**filters).exclude(**excludes).distinct()
        except ValueError:
            messages.error(self.request, _("Error during filtering."))

        return qs


class StorageDetail(SuperuserRequiredMixin, UpdateView):
    model = DataStore
    form_class = DataStoreForm
    template_name = "dashboard/storage/detail.html"

    def get_context_data(self, **kwargs):
        context = super(StorageDetail, self).get_context_data(**kwargs)
        try:
            ds = self.get_object()
            context['stats'] = self._get_stats()
            context['missing_disks'] = ds.get_missing_disks()
            context['orphan_disks'] = ds.get_orphan_disks()
        except WorkerNotFound:
            messages.error(self.request, _("The DataStore is offline."))
        except TimeoutError:
            messages.error(self.request, _("Operation timed out, "
                                           "some data may insufficient."))
        except Exception as e:
            messages.error(self.request, _("Error occured: %s, "
                                           "some data may insufficient."
                                           % unicode(e)))

        context['disk_table'] = DiskListTable(
            self.get_table_data(), request=self.request,
            template="django_tables2/with_pagination.html")
        context['filter_names'] = (
            ('vm', _("virtual machine")),
            ('template', _("template")),
            ('none', _("none")),
        )
        return context

    def get_table_data(self):
        ds = self.get_object()
        qs = Disk.objects.filter(datastore=ds, destroyed=None)

        filter_name = self.request.GET.get("filter")
        search = self.request.GET.get("s")

        filter_queries = {
            'vm': {
                'instance_set__isnull': False,
            },
            'template': {
                'template_set__isnull': False,
            },
            'none': {
                'template_set__isnull': True,
                'instance_set__isnull': True,
            }
        }

        if filter_name:
            qs = qs.filter(**filter_queries.get(filter_name, {}))

        if search:
            search = search.strip()
            qs = qs.filter(Q(name__icontains=search) |
                           Q(filename__icontains=search))

        return qs

    def _get_stats(self):
        stats = self.object.get_statistics()
        free_space = int(stats['free_space'])
        free_percent = float(stats['free_percent'])

        total_space = free_space / (free_percent/100.0)
        used_space = total_space - free_space

        return {
            'used_percent': int(100 - free_percent),
            'free_space': filesizeformat(free_space),
            'used_space': filesizeformat(used_space),
            'total_space': filesizeformat(total_space),
        }

    def get_form_class(self):
        ds = self.get_object()
        if ds.type == "ceph_block":
            return CephDataStoreForm
        else:
            return DataStoreForm

    def get_success_url(self):
        ds = self.get_object()
        return reverse("dashboard.views.storage-detail", kwargs={"pk": ds.id})


class DiskDetail(SuperuserRequiredMixin, UpdateView):
    model = Disk
    form_class = DiskForm
    template_name = "dashboard/storage/disk.html"

    def form_valid(self, form):
        pass


class EndpointCreate(SuccessMessageMixin, CreateView):
    model = Endpoint
    form_class = EndpointForm

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/_modal.html']
        else:
            return ['dashboard/nojs-wrapper.html']

    def get_context_data(self, *args, **kwargs):
        context = super(EndpointCreate, self).get_context_data(
            *args, **kwargs)

        context.update({
            'box_title': _("Create a new endpoint"),
            'ajax_title': True,
            'template': "dashboard/endpoint-create.html",
        })
        return context

    def get(self, *args, **kwargs):
        if not self.request.user.has_perm('storage.add_endpoint'):
            raise PermissionDenied()

        return super(EndpointCreate, self).get(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not self.request.user.has_perm('storage.add_endpoint'):
            raise PermissionDenied()

        form = self.form_class(request.POST)
        if not form.is_valid():
            if self.request.is_ajax():
                errors = self.errors_to_string(form)
                return self.json_response(False, errors)
            else:
                return self.get(request, form, *args, **kwargs)
        else:
            instance = form.save()
            if self.request.is_ajax():
                resp = {"val": instance.id, "text": unicode(instance)}
                return self.json_response(True, resp)
            else:
                return redirect(self.get_success_url())

    def json_response(self, status, response):
        resp = {
            "status": status,
            "response": response
        }
        return HttpResponse(json.dumps(resp), content_type="application/json")

    def errors_to_string(self, form):
        error_str = ""
        if form.errors:
            for field, error in form.errors.iteritems():
                    error_str += "%s: %s<br />" % (field, error)
            for error in form.non_field_errors():
                error_str += "%s<br />" % error

        return error_str

    def get_success_url(self):
        return reverse_lazy("dashboard.views.storage-endpoint-list")


class EndpointList(SuperuserRequiredMixin, FilterMixin, SingleTableView):
    template_name = "dashboard/endpoint-list.html"
    model = Endpoint
    table_class = EndpointListTable
    table_pagination = False

    allowed_filters = {
        'name': "name__icontains",
        'address': "address__icontains",
    }

    def get_context_data(self, *args, **kwargs):
        context = super(EndpointList, self).get_context_data(*args, **kwargs)
        context['search_form'] = self.search_form
        return context

    def get(self, *args, **kwargs):
        self.search_form = EndpointListSearchForm(self.request.GET)
        self.search_form.full_clean()

        return super(EndpointList, self).get(*args, **kwargs)

    def get_queryset(self):
        logger.debug('StorageList.get_queryset() called. User: %s',
                     unicode(self.request.user))
        qs = Endpoint.objects.all()
        self.create_fake_get()

        try:
            filters, excludes = self.get_queryset_filters()
            qs = qs.filter(**filters).exclude(**excludes).distinct()
        except ValueError:
            messages.error(self.request, _("Error during filtering."))

        return qs


class EndpointEdit(SuperuserRequiredMixin, UpdateView):
    model = Endpoint
    fields = ("name", "address", "port")
    template_name = "dashboard/endpoint-edit.html"

    def get_success_url(self):
        ds = self.get_object()
        return reverse_lazy("dashboard.views.storage-endpoint-edit",
                            kwargs={"pk": ds.id})


class EndpointDelete(SuperuserRequiredMixin, DeleteView):
    model = Endpoint
    success_message = _("Endpoint successfully deleted.")

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/confirm/ajax-delete.html']
        else:
            return ['dashboard/confirm/base-delete.html']

    def check_reference(self):
        object = self.get_object()
        if object.datastore_set.count() != 0:
            raise PermissionDenied()

    def get(self, request, *args, **kwargs):
        try:
            self.check_reference()
        except PermissionDenied:
            message = ugettext("Another object references"
                               " to the selected object.")
            if request.is_ajax():
                return JsonResponse({"error": message})
            else:
                messages.warning(request, message)
                return redirect(self.get_success_url())
        return super(EndpointDelete, self).get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("dashboard.views.storage-endpoint-list")

    def delete_obj(self, request, *args, **kwargs):
        self.get_object().delete()

    def delete(self, request, *args, **kwargs):
        self.check_reference()
        self.delete_obj(request, *args, **kwargs)

        if request.is_ajax():
            return HttpResponse(
                json.dumps({'message': self.success_message}),
                content_type="application/json",
            )
        else:
            messages.success(request, self.success_message)
            return HttpResponseRedirect(self.get_success_url())
