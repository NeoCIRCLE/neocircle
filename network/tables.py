from django_tables2 import Table, A
from django_tables2.columns import LinkColumn

from firewall.models import Host, Vlan, Domain, Group, Record


class DomainTable(Table):
    name = LinkColumn('network.domain', args=[A('pk')])

    class Meta:
        model = Domain
        attrs = {'class': 'table table-striped table-condensed'}
        fields = ('name', 'owner', 'ttl', )
        order_by = ('name', )


class GroupTable(Table):
    name = LinkColumn('network.group', args=[A('pk')])

    class Meta:
        model = Group
        attrs = {'class': 'table table-striped table-condensed'}
        fields = ('name', 'description', 'owner', )
        order_by = ('name', )


class HostTable(Table):
    hostname = LinkColumn('network.host', args=[A('pk')])

    class Meta:
        model = Host
        attrs = {'class': 'table table-striped table-condensed'}
        fields = ('hostname', 'vlan', 'mac', 'ipv4', 'ipv6',
                  'pub_ipv4', 'created_at', 'owner', )
        order_by = ('vlan', 'hostname', )


# inheritance by copy-paste
class SmallHostTable(Table):
    hostname = LinkColumn('network.host', args=[A('pk')])

    class Meta:
        model = Host
        attrs = {'class': 'table table-striped table-condensed'}
        fields = ('hostname', 'ipv4')
        order_by = ('vlan', 'hostname', )


class RecordTable(Table):
    fqdn = LinkColumn('network.record', args=[A('pk')])

    class Meta:
        model = Record
        attrs = {'class': 'table table-striped table-condensed'}
        fields = ('type', 'fqdn', 'address', 'ttl', 'host',
                  'owner', )
        sequence = ('type', 'fqdn', )
        order_by = 'name'


class VlanTable(Table):
    name = LinkColumn('network.vlan', args=[A('vid')])

    class Meta:
        model = Vlan
        attrs = {'class': 'table table-striped table-condensed'}
        fields = ('vid', 'name', 'interface', 'ipv4', 'ipv6', 'domain', )
        order_by = 'vid'
