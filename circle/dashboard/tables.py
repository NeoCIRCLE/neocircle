from django_tables2 import Table, A
from django_tables2.columns import Column, LinkColumn, TemplateColumn

from vm.models import Instance
from django.utils.translation import ugettext_lazy as _


class VmListTable(Table):
    name = LinkColumn('dashboard.views.detail', args=[A('pk')])
    admin = TemplateColumn(template_name='dashboard/vm-list/column-admin.html')
    details = TemplateColumn(template_name=
                             'dashboard/vm-list/column-details.html')
    actions = TemplateColumn(template_name=
                             'dashboard/vm-list/column-actions.html')
    time_of_suspend = TemplateColumn(
        '{{ record.time_of_suspend|timesince }}',
        verbose_name=_("Suspend in"))
    time_of_delete = Column(verbose_name=_("Delete in"))

    class Meta:
        model = Instance
        attrs = {'class': ('table table-bordered table-striped table-hover '
                           'vm-list-table')}
        fields = ('pk', 'name', 'state', 'time_of_suspend', 'time_of_delete', )
