from __future__ import absolute_import

from django.contrib.auth.models import Group, User
from django_tables2 import Table, A
from django_tables2.columns import (TemplateColumn, Column, BooleanColumn,
                                    LinkColumn)

from vm.models import Instance, Node, InstanceTemplate, Lease
from django.utils.translation import ugettext_lazy as _


class VmListTable(Table):
    pk = TemplateColumn(
        template_name='dashboard/vm-list/column-id.html',
        verbose_name="ID",
        attrs={'th': {'class': 'vm-list-table-thin'}},
    )

    name = TemplateColumn(
        template_name="dashboard/vm-list/column-name.html"
    )

    admin = TemplateColumn(
        template_name='dashboard/vm-list/column-admin.html',
        attrs={'th': {'class': 'vm-list-table-admin'}},
    )
    details = TemplateColumn(
        template_name='dashboard/vm-list/column-details.html',
        attrs={'th': {'class': 'vm-list-table-thin'}},
    )
    actions = TemplateColumn(
        template_name='dashboard/vm-list/column-actions.html',
        attrs={'th': {'class': 'vm-list-table-thin'}},
    )
    time_of_suspend = TemplateColumn(
        '{{ record.time_of_suspend|timeuntil }}',
        verbose_name=_("Suspend in"))
    time_of_delete = TemplateColumn(
        '{{ record.time_of_delete|timeuntil }}',
        verbose_name=_("Delete in"))

    class Meta:
        model = Instance
        attrs = {'class': ('table table-bordered table-striped table-hover '
                           'vm-list-table')}
        fields = ('pk', 'name', 'state', 'time_of_suspend', 'time_of_delete', )


class NodeListTable(Table):

    pk = Column(
        verbose_name="ID",
        attrs={'th': {'class': 'node-list-table-thin'}},
    )

    overcommit = Column(
        verbose_name="Overcommit",
        attrs={'th': {'class': 'node-list-table-thin'}},
    )

    host = Column(
        verbose_name="Host",
    )

    enabled = BooleanColumn(
        verbose_name="Enabled",
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
        template_name='dashboard/node-list/column-vm.html',
        attrs={'th': {'class': 'node-list-table-admin'}},
    )

    admin = TemplateColumn(
        template_name='dashboard/node-list/column-admin.html',
        attrs={'th': {'class': 'node-list-table-admin'}},
    )

    details = TemplateColumn(
        template_name='dashboard/node-list/column-details.html',
        attrs={'th': {'class': 'node-list-table-thin'}},
    )
    actions = TemplateColumn(
        attrs={'th': {'class': 'node-list-table-thin'}},
        template_code=('{% include "dashboard/node-list/column-'
                       'actions.html" with btn_size="btn-xs" %}'),
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
        template_name='dashboard/group-list/column-users.html',
        attrs={'th': {'class': 'group-list-table-admin'}},
    )

    admin = TemplateColumn(
        template_name='dashboard/group-list/column-admin.html',
        attrs={'th': {'class': 'group-list-table-admin'}},
    )

    actions = TemplateColumn(
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


class NodeVmListTable(Table):
    pk = TemplateColumn(
        template_name='dashboard/vm-list/column-id.html',
        verbose_name="ID",
        attrs={'th': {'class': 'vm-list-table-thin'}},
    )

    name = TemplateColumn(
        template_name="dashboard/vm-list/column-name.html"
    )

    admin = TemplateColumn(
        template_name='dashboard/vm-list/column-admin.html',
        attrs={'th': {'class': 'vm-list-table-admin'}},
    )
    details = TemplateColumn(
        template_name='dashboard/vm-list/column-details.html',
        attrs={'th': {'class': 'vm-list-table-thin'}},
    )
    actions = TemplateColumn(
        template_name='dashboard/vm-list/column-actions.html',
        attrs={'th': {'class': 'vm-list-table-thin'}},
    )
    time_of_suspend = TemplateColumn(
        '{{ record.time_of_suspend|timeuntil }}',
        verbose_name=_("Suspend in"))
    time_of_delete = TemplateColumn(
        '{{ record.time_of_delete|timeuntil }}',
        verbose_name=_("Delete in"))

    class Meta:
        model = Instance
        attrs = {'class': ('table table-bordered table-striped table-hover '
                           'vm-list-table')}
        fields = ('pk', 'name', 'state', 'time_of_suspend', 'time_of_delete', )


class UserListTablex(Table):
    class Meta:
        model = User


class TemplateListTable(Table):
    name = LinkColumn(
        'dashboard.views.template-detail',
        args=[A('pk')],
    )
    num_cores = Column(
        verbose_name=_("Cores"),
    )
    ram_size = TemplateColumn(
        "{{ record.ram_size }} Mb",
    )
    lease = TemplateColumn(
        "{{ record.lease.name }}",
        verbose_name=_("Lease"),
    )
    actions = TemplateColumn(
        verbose_name=_("Actions"),
        template_name="dashboard/template-list/column-template-actions.html",
        attrs={'th': {'class': 'template-list-table-thin'}},
    )

    class Meta:
        model = InstanceTemplate
        attrs = {'class': ('table table-bordered table-striped table-hover'
                           ' template-list-table')}
        fields = ('name', 'num_cores', 'ram_size', 'arch',
                  'system', 'access_method', 'lease', 'actions', )


class LeaseListTable(Table):
    name = LinkColumn(
        'dashboard.views.lease-detail',
        args=[A('pk')],
    )

    suspend_in = TemplateColumn(
        "{{ record.get_readable_suspend_time }}"
    )

    delete_in = TemplateColumn(
        "{{ record.get_readable_delete_time }}"
    )

    actions = TemplateColumn(
        verbose_name=_("Actions"),
        template_name="dashboard/template-list/column-lease-actions.html"
    )

    class Meta:
        model = Lease
        attrs = {'class': ('table table-bordered table-striped table-hover'
                           ' lease-list-table')}
        fields = ('name', 'suspend_in', 'delete_in', )
