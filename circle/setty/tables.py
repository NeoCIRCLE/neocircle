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

from django_tables2 import Table
from django_tables2.columns import TemplateColumn
from setty.models import Service
from django.utils.translation import ugettext as _


class ServiceListTable(Table):
    name = TemplateColumn(
        template_name="setty/tables/column-name.html",
        attrs={'th': {'data-sort': "string"}}
    )
    owner = TemplateColumn(
        template_name="setty/tables/column-owner.html",
        verbose_name=_("Owner"),
        attrs={'th': {'data-sort': "string"}}
    )
    running = TemplateColumn(
        template_name="setty/tables/column-running.html",
        verbose_name=_("Running"),
        attrs={'th': {'data-sort': "string"}},
    )

    class Meta:
        model = Service
        attrs = {'class': ('table table-bordered table-striped table-hover'
                           ' template-list-table')}
        fields = ('name', 'owner', 'running', )

        prefix = "service-"
