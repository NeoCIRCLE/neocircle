from django_tables2 import Table
from django_tables2.columns import TemplateColumn, Column, BooleanColumn

from vm.models import Instance, Node
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
        template_name="dashboard/node-list/column-name.html"
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
