from django_tables2 import Table, A
from django_tables2.columns import Column, LinkColumn, TemplateColumn

from vm.models import Instance
from django.utils.translation import ugettext_lazy as _


class VmListTable(Table):
    pk = TemplateColumn(
        template_name='dashboard/vm-list/column-id.html',
        verbose_name="ID",
        attrs={'th': {'class': 'vm-list-table-thin'}},
    )
    name = LinkColumn(
        'dashboard.views.detail',
        args=[A('pk')],
        attrs={'class': 'real-link'}
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
        '{{ record.time_of_suspend|timesince }}',
        verbose_name=_("Suspend in"))
    time_of_delete = Column(verbose_name=_("Delete in"))

    class Meta:
        model = Instance
        attrs = {'class': ('table table-bordered table-striped table-hover '
                           'vm-list-table')}
        fields = ('pk', 'name', 'state', 'time_of_suspend', 'time_of_delete', )
