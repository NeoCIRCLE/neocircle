from django_tables2 import Table, A
from django_tables2.columns import LinkColumn, TemplateColumn, Column

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
    )

    name = LinkColumn(
        'dashboard.views.node-detail',
        args=[A('pk')],
        attrs={'a': {'class': 'real-link'}}
    )

    class Meta:
        model = Node
        attrs = {'class': ('table table-bordered table-striped table-hover '
                           'node-list-table')}
        fields = ('pk', 'name', 'host', 'enabled', 'created', 'modified',
                  'priority', 'overcommit', )
