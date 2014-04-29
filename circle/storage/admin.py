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

from django import contrib
# from django.utils.translation import ugettext_lazy as _

from .models import Disk, DataStore, DiskActivity


class DiskAdmin(contrib.admin.ModelAdmin):
    list_display = ('id', 'name', 'base', 'type', 'datastore')
    ordering = ('-id', )


class DataStoreAdmin(contrib.admin.ModelAdmin):
    list_display = ('name', 'path')


contrib.admin.site.register(Disk, DiskAdmin)
contrib.admin.site.register(DiskActivity)
contrib.admin.site.register(DataStore, DataStoreAdmin)
