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

from __future__ import absolute_import

from django.contrib.auth.models import Group, User
from django_tables2 import Table, A
from django_tables2.columns import (TemplateColumn, Column, BooleanColumn,
                                    LinkColumn)

from vm.models import Node, InstanceTemplate, Lease
from django.utils.translation import ugettext_lazy as _
from django_sshkey.models import UserKey


class NodeListTable(Table):

    pk = Column(
        verbose_name="ID",
        attrs={'th': {'class': 'node-list-table-thin'}},
    )

    overcommit = Column(
        verbose_name=_("Overcommit"),
        attrs={'th': {'class': 'node-list-table-thin'}},
    )

    host = Column(
        verbose_name=_("Host"),
    )

    enabled = BooleanColumn(
        verbose_name=_("Enabled"),
        attrs={'th': {'class': 'node-list-table-thin'}},
    )

    name = TemplateColumn(
        template_name="dashboard/node-list/column-name.html",
        order_by="normalized_name"
    )

    priority = Column(
        verbose_name=_("Priority"),
        attrs={'th': {'class': 'node-list-table-thin'}},
    )

    number_of_VMs = TemplateColumn(
        verbose_name=_("Number of VMs"),
        template_name='dashboard/node-list/column-vm.html',
        attrs={'th': {'class': 'node-list-table-thin'}},
    )

    monitor = TemplateColumn(
        template_name='dashboard/node-list/column-monitor.html',
        attrs={'th': {'class': 'node-list-table-monitor'}},
        orderable=False,
    )

    actions = TemplateColumn(
        attrs={'th': {'class': 'node-list-table-thin'}},
        template_code=('{% include "dashboard/node-list/column-'
                       'actions.html" with btn_size="btn-xs" %}'),
        orderable=False,
    )

    class Meta:
        model = Node
        attrs = {'class': ('table table-bordered table-striped table-hover '
                           'node-list-table')}
        fields = ('pk', 'name', 'host', 'enabled', 'priority', 'overcommit',
                  'number_of_VMs', )


class GroupListTable(Table):
    pk = TemplateColumn(
        template_name='dashboard/group-list/column-id.html',
        verbose_name="ID",
        attrs={'th': {'class': 'group-list-table-thin'}},
    )

    name = TemplateColumn(
        template_name="dashboard/group-list/column-name.html"
    )

    number_of_users = TemplateColumn(
        orderable=False,
        template_name='dashboard/group-list/column-users.html',
        attrs={'th': {'class': 'group-list-table-admin'}},
    )

    admin = TemplateColumn(
        orderable=False,
        template_name='dashboard/group-list/column-admin.html',
        attrs={'th': {'class': 'group-list-table-admin'}},
    )

    actions = TemplateColumn(
        orderable=False,
        attrs={'th': {'class': 'group-list-table-thin'}},
        template_code=('{% include "dashboard/group-list/column-'
                       'actions.html" with btn_size="btn-xs" %}'),
    )

    class Meta:
        model = Group
        attrs = {'class': ('table table-bordered table-striped table-hover '
                           'group-list-table')}
        fields = ('pk', 'name', )


class UserListTable(Table):
    pk = TemplateColumn(
        template_name='dashboard/vm-list/column-id.html',
        verbose_name="ID",
        attrs={'th': {'class': 'vm-list-table-thin'}},
    )

    username = TemplateColumn(
        template_name="dashboard/group-list/column-username.html"
    )

    class Meta:
        model = User
        attrs = {'class': ('table table-bordered table-striped table-hover '
                           'vm-list-table')}
        fields = ('pk', 'username', )


class UserListTablex(Table):
    class Meta:
        model = User


class TemplateListTable(Table):
    name = LinkColumn(
        'dashboard.views.template-detail',
        args=[A('pk')],
        attrs={'th': {'data-sort': "string"}}
    )
    num_cores = Column(
        verbose_name=_("Cores"),
        attrs={'th': {'data-sort': "int"}}
    )
    ram_size = TemplateColumn(
        "{{ record.ram_size }} Mb",
        attrs={'th': {'data-sort': "string"}}
    )
    lease = TemplateColumn(
        "{{ record.lease.name }}",
        verbose_name=_("Lease"),
        attrs={'th': {'data-sort': "string"}}
    )
    arch = Column(
        attrs={'th': {'data-sort': "string"}}
    )
    system = Column(
        attrs={'th': {'data-sort': "string"}}
    )
    access_method = Column(
        attrs={'th': {'data-sort': "string"}}
    )
    actions = TemplateColumn(
        verbose_name=_("Actions"),
        template_name="dashboard/template-list/column-template-actions.html",
        attrs={'th': {'class': 'template-list-table-thin'}},
        orderable=False,
    )

    class Meta:
        model = InstanceTemplate
        attrs = {'class': ('table table-bordered table-striped table-hover'
                           ' template-list-table')}
        fields = ('name', 'num_cores', 'ram_size', 'arch',
                  'system', 'access_method', 'lease', 'actions', )

        prefix = "template-"


class LeaseListTable(Table):
    name = LinkColumn(
        'dashboard.views.lease-detail',
        args=[A('pk')],
    )

    suspend_interval_seconds = TemplateColumn(
        "{{ record.get_readable_suspend_time }}"
    )

    delete_interval_seconds = TemplateColumn(
        "{{ record.get_readable_delete_time }}"
    )

    actions = TemplateColumn(
        verbose_name=_("Actions"),
        template_name="dashboard/template-list/column-lease-actions.html",
        orderable=False,
    )

    class Meta:
        model = Lease
        attrs = {'class': ('table table-bordered table-striped table-hover'
                           ' lease-list-table')}
        fields = ('name', 'suspend_interval_seconds',
                  'delete_interval_seconds', )
        prefix = "lease-"


class UserKeyListTable(Table):
    name = LinkColumn(
        'dashboard.views.userkey-detail',
        args=[A('pk')],
        verbose_name=_("Name"),
        attrs={'th': {'data-sort': "string"}}
    )

    fingerprint = Column(
        verbose_name=_("Fingerprint"),
        attrs={'th': {'data-sort': "string"}}
    )

    created = Column(
        verbose_name=_("Created at"),
        attrs={'th': {'data-sort': "string"}}
    )

    actions = TemplateColumn(
        verbose_name=_("Actions"),
        template_name="dashboard/userkey-list/column-userkey-actions.html",
        orderable=False,
    )

    class Meta:
        model = UserKey
        attrs = {'class': ('table table-bordered table-striped table-hover')}
        fields = ('name', 'fingerprint', 'created', 'actions')
