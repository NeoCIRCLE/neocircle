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

from django.forms import ModelForm
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Div, Submit, BaseInput
from crispy_forms.bootstrap import FormActions

from firewall.models import (Host, Vlan, Domain, Group, Record, BlacklistItem,
                             Rule, VlanGroup, SwitchPort)


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
                'reason',
                'type',
            )
        ),
        FormActions(
            Submit('submit', _('Save changes')),
            LinkButton('back', _("Back"), reverse_lazy('network.blacklist_list'))
        )
    )

    class Meta:
        model = BlacklistItem


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
                'ipv4',
                'ipv6',
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
                'ipv6_template',
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
