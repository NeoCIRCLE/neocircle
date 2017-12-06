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

from django.forms import ModelForm, widgets
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Div, Submit, BaseInput, Field
from crispy_forms.bootstrap import FormActions, FieldWithButtons, StrictButton

from firewall.models import (
    Host, Vlan, Domain, Group, Record, BlacklistItem, Rule, VlanGroup,
    SwitchPort, Firewall
)
from network.models import Vxlan


class LinkButton(BaseInput):
    """
    Used to create a link button descriptor for the {% crispy %} template tag::

        back = LinkButton('back', 'Back', reverse_lazy('index'))

    .. note:: The first argument is also slugified and turned into the id for
              the submit button.
    """
    template = "bootstrap/layout/linkbutton.html"
    field_classes = 'btn btn-default'

    def __init__(self, name, text, url, *args, **kwargs):
        self.href = url
        super(LinkButton, self).__init__(name, text, *args, **kwargs)


class BlacklistItemForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        Div(
            Fieldset(
                '',
                'ipv4',
                'host',
                'expires_at',
                'whitelisted',
                'reason',
                'snort_message',
            )
        ),
        FormActions(
            Submit('submit', _('Save changes')),
            LinkButton('back', _("Back"),
                       reverse_lazy('network.blacklist_list'))
        )
    )

    class Meta:
        model = BlacklistItem
        fields = ("ipv4", "host", "expires_at", "whitelisted", "reason",
                  "snort_message", )


class DomainForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        Div(
            Fieldset(
                '',
                'name',
                'ttl',
                'owner',
            ),
        ),
        FormActions(
            Submit('submit', _('Save')),
            LinkButton('back', _("Back"), reverse_lazy('network.domain_list'))
        )
    )

    class Meta:
        model = Domain
        fields = ("name", "ttl", "owner", )


class FirewallForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        Div(Fieldset('', 'name', )),
        FormActions(
            Submit('submit', _("Save")),
            LinkButton('back', _("Back"),
                       reverse_lazy('network.firewall_list'))
        )
    )

    class Meta:
        model = Firewall
        fields = ("name", )


class GroupForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        Div(
            Fieldset(
                '',
                'name',
                'description',
                'owner',
            ),
        ),
        FormActions(
            Submit('submit', _('Save')),
            LinkButton('back', _("Back"), reverse_lazy('network.group_list'))
        )
    )

    class Meta:
        model = Group
        fields = ("name", "description", "owner", )


class HostForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        Div(
            Fieldset(
                '',
                'hostname',
                'reverse',
                'mac',
            ),
            Fieldset(
                _('Network'),
                'vlan',
                FieldWithButtons('ipv4', StrictButton(
                    '<i class="fa fa-magic"></i>', css_id="ipv4-magic",
                    title=_("Generate random address."))),
                FieldWithButtons('ipv6', StrictButton(
                    '<i class="fa fa-magic"></i>', css_id="ipv6-magic",
                    title=_("Generate IPv6 pair of IPv4 address."))),
                'shared_ip',
                'external_ipv4',
            ),
            Fieldset(
                _('Information'),
                'description',
                'location',
                'comment',
                'owner',
            ),
        ),
        FormActions(
            Submit('submit', _('Save')),
            LinkButton('back', _('Back'), reverse_lazy('network.host_list')))
    )

    class Meta:
        model = Host
        fields = ("hostname", "reverse", "mac", "vlan", "shared_ip", "ipv4",
                  "ipv6", "external_ipv4", "description", "location",
                  "comment", "owner", )


class RecordForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        Div(
            Fieldset(
                '',
                'type',
                'host',
                'name',
                'domain',
                'address',
                'ttl',
                'description',
                'owner',
            )
        ),
        FormActions(
            Submit('submit', _("Save")),
            LinkButton('back', _("Back"), reverse_lazy('network.record_list'))
        )
    )

    class Meta:
        model = Record
        fields = ("type", "host", "name", "domain", "address", "ttl",
                  "description", "owner", )


class RuleForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        Div(
            Fieldset(
                '',
                'direction',
                'description',
                'foreign_network',
                'dport',
                'sport',
                'weight',
                'proto',
                'extra',
                'action',
                'owner',
                'nat',
                'nat_external_port',
                'nat_external_ipv4',
            ),
            Fieldset(
                _('External'),
                'vlan',
                'vlangroup',
                'host',
                'hostgroup',
                'firewall'
            )
        ),
        FormActions(
            Submit('submit', _("Save")),
            LinkButton('back', _("Back"), reverse_lazy('network.rule_list'))
        )
    )

    class Meta:
        model = Rule
        fields = ("direction", "description", "foreign_network", "dport",
                  "sport", "weight", "proto", "extra", "action", "owner",
                  "nat", "nat_external_port", "nat_external_ipv4", "vlan",
                  "vlangroup", "host", "hostgroup", "firewall", )


class SwitchPortForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        Div(
            Fieldset(
                '',
                'untagged_vlan',
                'tagged_vlans',
                'description',
            )
        ),
        FormActions(
            Submit('submit', _("Save")),
            LinkButton('back', _("Back"),
                       reverse_lazy('network.switch_port_list'))
        )
    )

    class Meta:
        model = SwitchPort
        fields = ("untagged_vlan", "tagged_vlans", "description", )


class VlanForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        Div(
            Fieldset(
                '',
                'name',
                'vid',
                'network_type',
                'managed',
            ),
            Fieldset(
                _('IPv4'),
                'network4',
                'snat_to',
                'snat_ip',
                'dhcp_pool',
            ),
            Fieldset(
                _('IPv6'),
                'network6',
                FieldWithButtons('ipv6_template', StrictButton(
                    '<i class="fa fa-magic"></i>', css_id="ipv6-tpl-magic",
                    title=_("Generate sensible template."))),
                'host_ipv6_prefixlen',
            ),
            Fieldset(
                _('Domain name service'),
                'domain',
                'reverse_domain',
            ),
            Fieldset(
                _('Info'),
                'description',
                'comment',
                'owner',
                # 'created_at',
                # 'modified_at',
            ),
        ),
        FormActions(
            Submit('submit', _("Save")),
            LinkButton('back', _("Back"), reverse_lazy('network.vlan_list'))
        )
    )

    class Meta:
        model = Vlan
        widgets = {
            'ipv6_template': widgets.TextInput,
        }
        fields = ("name", "vid", "network_type", "managed", "network4",
                  "snat_to", "snat_ip", "dhcp_pool", "network6",
                  "ipv6_template", "host_ipv6_prefixlen", "domain",
                  "reverse_domain", "description", "comment", "owner", )


class VlanGroupForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        Div(
            Fieldset(
                '',
                'name',
                'vlans',
                'description',
                'owner',
            )
        ),
        FormActions(
            Submit('submit', _("Save")),
            LinkButton('back', _("Back"), reverse_lazy(
                'network.vlan_group_list'))
        )
    )

    class Meta:
        model = VlanGroup
        fields = ("name", "vlans", "description", "owner", )


class VxlanSuperUserForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        Div(
            Fieldset(
                '',
                'name',
                'vni',
                'vlan',
                'description',
                'comment',
                'owner',
            )
        ),
        FormActions(
            Submit('submit', _('Save')),
            LinkButton('back', _('Back'), reverse_lazy(
                'network.vxlan-list'))
        )
    )

    class Meta:
        model = Vxlan
        fields = ('name', 'vni', 'vlan', 'description', 'comment', 'owner', )


class VxlanForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        Div(
            Fieldset(
                '',
                'name',
                'description',
                'comment',
                Field('vni', type='hidden'),
            )
        ),
        FormActions(
            Submit('submit', _('Save')),
            LinkButton('back', _('Back'), reverse_lazy(
                'network.vxlan-list'))
        )
    )

    class Meta:
        model = Vxlan
        fields = ('name', 'description', 'comment', 'vni', )
