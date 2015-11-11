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

from django.contrib import messages
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.views.generic import UpdateView

from braces.views import SuperuserRequiredMixin
from sizefield.utils import filesizeformat

from common.models import WorkerNotFound
from storage.models import DataStore, Disk
from ..tables import DiskListTable
from ..forms import DataStoreForm, DiskForm


class StorageDetail(SuperuserRequiredMixin, UpdateView):
    model = DataStore
    form_class = DataStoreForm
    template_name = "dashboard/storage/detail.html"

    def get_object(self):
        return DataStore.get_default_datastore()

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
