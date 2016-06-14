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
from storage.models import DataStore, Disk
from ..tables import DiskListTable, StorageListTable
from ..forms import (
    DataStoreForm, CephDataStoreForm, DiskForm, StorageListSearchForm
)
from .util import FilterMixin
import json
from celery.exceptions import TimeoutError

from vm.models import Node

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
        cleaned_data = self.search_form.cleaned_data
        stype = cleaned_data.get('stype', "all")
        qs = self.get_queryset_by_stype(stype)
        self.create_fake_get()

        try:
            filters, excludes = self.get_queryset_filters()
            qs = qs.filter(**filters).exclude(**excludes).distinct()
        except ValueError:
            messages.error(self.request, _("Error during filtering."))

        return qs

    def get_queryset_by_stype(self, stype):
        if stype == "all":
            return DataStore.get_all()
        elif stype == "destroyed":
            return DataStore.objects.filter(destroyed__isnull=False)
        else:
            return DataStore.objects.filter(destroyed__isnull=True)


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

    def form_valid(self, form):
        # automatic credential refresh
        changed = False
        if self.object.type == "ceph_block":
            changed = (self.object.tracker.has_changed("secret")
                       or self.object.tracker.has_changed("ceph_user"))
        response = super(StorageDetail, self).form_valid(form)
        if changed:
            nodes = Node.objects.all()
            for node in nodes:
                if node.get_online():
                    node.refresh_credential(
                        user=self.request.user,
                        username=self.object.ceph_user,
                        secret=self.object.secret)
        return response


class StorageDelete(SuperuserRequiredMixin, DeleteView):
    model = DataStore
    success_message = _("Storage successfully destroyed.")

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/confirm/ajax-delete.html']
        else:
            return ['dashboard/confirm/base-delete.html']

    def check_destroyable(self):
        object = self.get_object()
        if not object.is_destroyable:
            raise PermissionDenied()

    def get(self, request, *args, **kwargs):
        try:
            self.check_destroyable()
        except PermissionDenied:
            message = ugettext("Another object references"
                               " to the selected object.")
            if request.is_ajax():
                return JsonResponse({"error": message})
            else:
                messages.warning(request, message)
                return redirect(self.get_success_url())
        return super(StorageDelete, self).get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("dashboard.views.storage-list")

    def delete_obj(self, request, *args, **kwargs):
        self.get_object().destroy()

    def delete(self, request, *args, **kwargs):
        self.check_destroyable()
        self.delete_obj(request, *args, **kwargs)

        if request.is_ajax():
            return JsonResponse(
                json.dumps({'message': self.success_message}),
            )
        else:
            messages.success(request, self.success_message)
            return HttpResponseRedirect(self.get_success_url())


class StorageRestore(SuperuserRequiredMixin, UpdateView):

    model = DataStore
    fields = ("destroyed",)
    success_message = _("Data store successfully restored.")

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/confirm/ajax-restore.html']
        else:
            return ['dashboard/confirm/base-restore.html']

    def form_valid(self, form):
        object = self.get_object()
        object.destroyed = None
        object.save()

        if self.request.is_ajax():
            return JsonResponse(
                json.dumps({'message': self.success_message}),
            )
        else:
            messages.success(self.request, self.success_message)
            return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        ds = self.get_object()
        return reverse_lazy("dashboard.views.storage-detail",
                            kwargs={"pk": ds.id})


class DiskDetail(SuperuserRequiredMixin, UpdateView):
    model = Disk
    form_class = DiskForm
    template_name = "dashboard/storage/disk.html"

    def form_valid(self, form):
        pass
