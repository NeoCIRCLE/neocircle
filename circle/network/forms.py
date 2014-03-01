from django.forms import ModelForm
from django.core.urlresolvers import reverse_lazy

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Div, Submit, BaseInput
from crispy_forms.bootstrap import FormActions

from firewall.models import (Host, Vlan, Domain, Group, Record, Blacklist,
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


class BlacklistForm(ModelForm):
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
            Submit('submit', 'Save changes'),
            LinkButton('back', 'Back', reverse_lazy('network.blacklist_list'))
        )
    )

    class Meta:
        model = Blacklist


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
            Submit('submit', 'Save'),
            LinkButton('back', 'Back', reverse_lazy('network.domain_list'))
        )
    )

    class Meta:
        model = Domain


class GroupForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        Div(
            Fieldset(
                'Identity',
                'name',
                'description',
                'owner',
            ),
        ),
        FormActions(
            Submit('submit', 'Save'),
            LinkButton('back', 'Back', reverse_lazy('network.group_list'))
        )
    )

    class Meta:
        model = Group


class HostForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        Div(
            Fieldset(
                'Identity',
                'hostname',
                'reverse',
                'mac',
            ),
            Fieldset(
                'Network',
                'vlan',
                'ipv4',
                'ipv6',
                'shared_ip',
                'pub_ipv4',
            ),
            Fieldset(
                'Information',
                'description',
                'location',
                'comment',
                'owner',
            ),
        ),
        FormActions(
            Submit('submit', 'Save'),
            LinkButton('back', 'Back', reverse_lazy('network.host_list')))
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
            Submit('submit', 'Save'),
            LinkButton('back', 'Back', reverse_lazy('network.record_list'))
        )
    )

    class Meta:
        model = Record


class RuleForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        Div(
            Fieldset(
                'Identity',
                'direction',
                'description',
                'foreign_network',
                'dport',
                'sport',
                'proto',
                'extra',
                'accept',
                'owner',
                'nat',
                'nat_external_port',
                'nat_external_ipv4',
            ),
            Fieldset(
                'External',
                'vlan',
                'vlangroup',
                'host',
                'hostgroup',
                'firewall'
            )
        ),
        FormActions(
            Submit('submit', 'Save'),
            LinkButton('back', 'Back', reverse_lazy('network.rule_list'))
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
            Submit('submit', 'Save'),
            LinkButton('back', 'Back',
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
                'Identity',
                'name',
                'vid',
                'network_type',
                'managed',
            ),
            Fieldset(
                'IPv4',
                'network4',
                'snat_to',
                'snat_ip',
                'dhcp_pool',
            ),
            Fieldset(
                'IPv6',
                'network6',
                'ipv6_template',
            ),
            Fieldset(
                'Domain name service',
                'domain',
                'reverse_domain',
            ),
            Fieldset(
                'Info',
                'description',
                'comment',
                # 'created_at',
                # 'modified_at',
            ),
        ),
        FormActions(
            Submit('submit', 'Save'),
            LinkButton('back', 'Back', reverse_lazy('network.vlan_list'))
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
            Submit('submit', 'Save'),
            LinkButton('back', 'Back', reverse_lazy(
                'network.vlan_group_list'))
        )
    )

    class Meta:
        model = VlanGroup
