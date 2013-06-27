from django.views.generic import TemplateView
from django.views.generic import UpdateView

from django_tables2 import SingleTableView, Table, A
from django_tables2.columns import LinkColumn

from firewall.models import Host


class IndexView(TemplateView):
    template_name = "network/index.html"


class HostTable(Table):
    hostname = LinkColumn('network.host', args=[A('pk')])

    class Meta:
        model = Host
        attrs = {'class': 'table table-striped table-condensed'}
        fields = ('hostname', 'vlan', 'mac', 'ipv4', 'ipv6',
                  'pub_ipv4', 'created_at', 'owner', )


class HostList(SingleTableView):
    model = Host
    table_class = HostTable
    template_name = "network/host-list.html"


class HostDetail(UpdateView):
    model = Host
    template_name = "network/host-edit.html"
