from django_tables2 import Table, A
from django_tables2.columns import LinkColumn, TemplateColumn

from firewall.models import Host, Vlan, Domain, Group, Record, Rule, SwitchPort


class BlacklistTable(Table):
    ipv4 = LinkColumn('network.blacklist', args=[A('pk')])

    class Meta:
        model = Domain
        attrs = {'class': 'table table-striped table-condensed'}
        fields = ('ipv4', 'host', 'reason', 'type')
        order_by = ('ipv4', )


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
    mac = TemplateColumn(
        template_name="network/columns/mac.html"
    )

    class Meta:
        model = Host
        attrs = {'class': 'table table-striped table-condensed'}
        fields = ('hostname', 'vlan', 'mac', 'ipv4', 'ipv6',
                  'external_ipv4', 'created_at', 'owner', )
        order_by = ('vlan', 'hostname', )


class SmallRuleTable(Table):
    rule = TemplateColumn(
        template_name="network/columns/host-rule.html",
        attrs={"th": {"style": "display: none;"}}
    )

    action = TemplateColumn(
        template_name="network/columns/host-rule-action.html",
        attrs={
            "th": {"style": "display: none;"},
            "cell": {"style": "text-align: center; vertical-align: middle;"}
        }
    )

    class Meta:
        model = Rule
        attrs = {'class': 'table table-striped table-bordered table-condensed'}
        fields = ('rule', 'action', )


class SmallGroupRuleTable(Table):
    rule = TemplateColumn(
        template_name="network/columns/host-rule.html",
        attrs={"th": {"style": "display: none;"}}
    )

    class Meta:
        model = Rule
        attrs = {'class': 'table table-striped table-bordered table-condensed'}
        fields = ('rule', )


# inheritance by copy-paste
class SmallHostTable(Table):
    hostname = LinkColumn('network.host', args=[A('pk')])

    class Meta:
        model = Host
        attrs = {'class': 'table table-striped table-condensed'}
        fields = ('hostname', 'ipv4')
        order_by = ('vlan', 'hostname', )


class RecordTable(Table):
    fqdn = LinkColumn('network.record', args=[A('pk')], orderable=False)
    address = TemplateColumn(
        template_name="network/columns/records-address.html"
    )

    class Meta:
        model = Record
        attrs = {'class': 'table table-striped table-condensed'}
        fields = ('type', 'fqdn', 'host', 'address', 'ttl', 'host',
                  'owner', )
        sequence = ('type', 'fqdn', )
        #order_by = 'name'


class SmallRecordTable(Table):
    fqdn = LinkColumn('network.record', args=[A('pk')], orderable=False)

    class Meta:
        model = Record
        attrs = {'class': 'table table-striped table-bordered'}
        fields = ('type', 'fqdn', 'host', 'address', )
        sequence = ('type', 'fqdn', )
        #order_by = '-type'
        orderable = False


class RuleTable(Table):
    r_type = LinkColumn('network.rule', args=[A('pk')])
    color_desc = TemplateColumn(
        template_name="network/columns/color-desc.html"
    )

    class Meta:
        model = Rule
        attrs = {'class': 'table table-striped table-hover table-condensed'}
        fields = ('r_type', 'color_desc', 'owner', 'extra', 'direction',
                  'accept', 'proto', 'sport', 'dport', 'nat',
                  'nat_external_port', )
        order_by = 'direction'


class SwitchPortTable(Table):
    pk = LinkColumn('network.switch_port', args=[A('pk')],
                    verbose_name="ID")

    class Meta:
        model = SwitchPort
        attrs = {'class': 'table table-striped table-condensed'}
        fields = ('pk', 'untagged_vlan', 'tagged_vlans', 'description', )
        order_by = 'pk'


class VlanTable(Table):
    name = LinkColumn('network.vlan', args=[A('vid')])

    class Meta:
        model = Vlan
        attrs = {'class': 'table table-striped table-condensed'}
        fields = ('vid', 'name', 'interface', 'network4', 'network6',
                  'domain', )
        order_by = 'vid'


class VlanGroupTable(Table):
    name = LinkColumn('network.vlan_group', args=[A('pk')])
    vlans = TemplateColumn(template_name="network/columns/vlan-list.html")

    class Meta:
        model = Vlan
        attrs = {'class': 'table table-striped table-condensed'}
        fields = ('name', 'vlans', 'description', 'owner', )
        order_by = 'name'
