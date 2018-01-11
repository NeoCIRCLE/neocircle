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

from netaddr import EUI
from django.utils.translation import ugettext_lazy as _
from django.utils.html import format_html

from django_tables2 import Table, A
from django_tables2.columns import (LinkColumn, TemplateColumn, Column,
                                    BooleanColumn)

from firewall.models import Host, Vlan, Domain, Group, Record, Rule, SwitchPort


class MACColumn(Column):
    def render(self, value):
        if isinstance(value, basestring):
            try:
                value = EUI(value)
            except:
                return value
        try:
            return format_html('<abbr title="{0}">{1}</abbr>',
                               value.oui.registration().org, value)
        except:
            return value


class BlacklistItemTable(Table):
    ipv4 = LinkColumn('network.blacklist', args=[A('pk')])
    whitelisted = BooleanColumn()

    class Meta:
        model = Domain
        attrs = {'class': 'table table-striped table-condensed'}
        fields = ('ipv4', 'host', 'reason', 'whitelisted', 'expires_at',
                  'created_at')
        order_by = ('-expires_at', )


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
    hostname = LinkColumn(
        'network.host',
        args=[A('pk')],
        order_by="normalized_hostname",
    )
    mac = MACColumn()

    class Meta:
        model = Host
        attrs = {'class': "table table-striped table-condensed",
                 'id': "network-host-list-table"}
        fields = ('hostname', 'vlan', 'mac', 'ipv4', 'ipv6',
                  'external_ipv4', 'created_at', 'owner', )
        order_by = ("hostname", )


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
        attrs = {'class': 'table table-striped table-condensed',
                 'id': "small_rule_table"}
        fields = ('rule', 'action', )


class SmallGroupRuleTable(Table):
    rule = TemplateColumn(
        template_name="network/columns/host-rule.html",
        attrs={"th": {"style": "display: none;"}}
    )

    class Meta:
        model = Rule
        attrs = {'class': 'table table-striped table-condensed'}
        fields = ('rule', )


# inheritance by copy-paste
class SmallHostTable(Table):
    hostname = LinkColumn('network.host', args=[A('pk')])

    class Meta:
        model = Host
        attrs = {'class': 'table table-striped table-condensed'}
        fields = ('hostname', 'ipv4')
        order_by = ('vlan', 'hostname', )
        empty_text = _("No hosts.")


class SmallDhcpTable(Table):
    mac = MACColumn(verbose_name=_("MAC address"))
    hostname = Column(verbose_name=_("hostname"))
    ip = Column(verbose_name=_("requested IP"))
    register = TemplateColumn(
        template_name="network/columns/host-register.html",
        attrs={"th": {"style": "display: none;"}})

    class Meta:
        attrs = {'class': 'table table-striped table-condensed'}
        empty_text = _("No hosts.")


class RecordTable(Table):
    fqdn = LinkColumn('network.record', args=[A('pk')], orderable=False)
    address = TemplateColumn(
        template_name="network/columns/records-address.html"
    )
    ttl = Column(verbose_name=_("TTL"))

    class Meta:
        model = Record
        attrs = {'class': 'table table-striped table-condensed'}
        fields = ('type', 'fqdn', 'host', 'address', 'ttl', 'host',
                  'owner', )
        sequence = ('type', 'fqdn', )
        # order_by = 'name'


class SmallRecordTable(Table):
    fqdn = LinkColumn('network.record', args=[A('pk')], orderable=False)

    class Meta:
        model = Record
        attrs = {'class': 'table table-striped'}
        fields = ('type', 'fqdn', 'host', 'address', )
        sequence = ('type', 'fqdn', )
        # order_by = '-type'
        orderable = False


class RuleTable(Table):
    r_type = LinkColumn(
        'network.rule', args=[A('pk')],
        verbose_name=_("type"),
        orderable=False,
    )
    color_desc = TemplateColumn(
        template_name="network/columns/rule-short-description.html",
        verbose_name=_("Short description"),
        orderable=False,
    )
    nat_external_port = Column(
        verbose_name=_("NAT")
    )

    class Meta:
        model = Rule
        attrs = {'class': 'table table-striped table-hover table-condensed',
                 'id': "rule-list-table"}
        fields = ('r_type', 'color_desc', 'extra', 'direction',
                  'action', 'proto', 'dport',
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
        fields = ('vid', 'name', 'network4', 'network6',
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


class HostRecordsTable(Table):
    fqdn = LinkColumn(
        "network.record", args=[A("pk")],
        order_by=("name", ),
    )

    class Meta:
        model = Record
        attrs = {
            'class': "table table-striped",
            'id': "host-detail-records-table",
        }
        fields = ("type", "fqdn")
        order_by = ("name", )
        empty_text = _("No records.")


class FirewallTable(Table):
    pk = LinkColumn('network.firewall', args=[A('pk')],
                    verbose_name="ID")

    class Meta:
        model = SwitchPort
        attrs = {'class': 'table table-striped'}
        fields = ('pk', 'name', )
        order_by = 'pk'


class FirewallRuleTable(Table):
    color_desc = TemplateColumn(
        template_name="network/columns/rule-short-description.html",
        verbose_name=_("Short description"),
        orderable=False,
    )
    actions = TemplateColumn(
        template_name="network/columns/firewall-rule-actions.html",
        verbose_name=_("Actions"),
        orderable=False,
    )

    class Meta:
        model = Rule
        template = "django_tables2/table_no_page.html"
        attrs = {'class': 'table table-striped table-hover table-condensed',
                 'id': "rule-list-table"}
        fields = ('color_desc', 'extra', 'direction',
                  'action', 'proto', 'actions')
        order_by = '-pk'
        empty_text = _("No related rules found.")
