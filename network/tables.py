from django_tables2 import Table, A
from django_tables2.columns import LinkColumn

from firewall.models import Host, Vlan


class HostTable(Table):
    hostname = LinkColumn('network.host', args=[A('pk')])

    class Meta:
        model = Host
        attrs = {'class': 'table table-striped table-condensed'}
        fields = ('hostname', 'vlan', 'mac', 'ipv4', 'ipv6',
                  'pub_ipv4', 'created_at', 'owner', )
        order_by = ('vlan', 'hostname', )


class VlanTable(Table):
    name = LinkColumn('network.vlan', args=[A('pk')])

    class Meta:
        model = Vlan
        attrs = {'class': 'table table-striped table-condensed'}
        fields = ('vid', 'name', 'interface', 'ipv4', 'ipv6', 'domain', )
        order_by = 'vid'
