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
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.views.generic import UpdateView
from django_tables2 import SingleTableView

from braces.views import SuperuserRequiredMixin, LoginRequiredMixin
from sizefield.utils import filesizeformat

from common.models import WorkerNotFound
from storage.models import DataStore, Disk
from ..tables import DiskListTable, StorageListTable
from ..forms import DataStoreForm, DiskForm, StorageListSearchForm
from .util import FilterMixin


logger = logging.getLogger(__name__)


class StorageList(LoginRequiredMixin, FilterMixin, SingleTableView):
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
        'address': "hosts__address__in"
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

    def get_success_url(self):
        return reverse("dashboard.views.storage")


class DiskDetail(SuperuserRequiredMixin, UpdateView):
    model = Disk
    form_class = DiskForm
    template_name = "dashboard/storage/disk.html"

    def form_valid(self, form):
        pass
