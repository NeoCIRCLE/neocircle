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
    UpdateView
)
from django.core.urlresolvers import reverse

from sizefield.utils import filesizeformat

from storage.models import DataStore, Disk
from ..tables import DiskListTable
from ..forms import DataStoreForm


class StorageDetail(UpdateView):
    model = DataStore
    form_class = DataStoreForm
    template_name = "dashboard/storage/detail.html"

    def get_object(self):
        return DataStore.objects.get()

    def get_context_data(self, **kwargs):
        context = super(StorageDetail, self).get_context_data(**kwargs)

        ds = self.get_object()
        context['stats'] = self._get_stats()
        context['missing_disks'] = ds.get_missing_disks()
        context['orphan_disks'] = ds.get_orphan_disks()
        qs = Disk.objects.filter(datastore=ds, destroyed=None)
        context['disk_table'] = DiskListTable(
            qs, request=self.request,
            template="django_tables2/table_no_page.html")
        return context

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
