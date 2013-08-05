from django.forms import ModelForm
from django.core.urlresolvers import reverse_lazy

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Row, HTML
from crispy_forms.layout import Div, ButtonHolder, Submit, BaseInput

from firewall.models import (Host, Vlan, Domain, Group, Record, Blacklist,
                             Rule, VlanGroup)


class LinkButton(BaseInput):
    """
    Used to create a link button descriptor for the {% crispy %} template tag::

        back = LinkButton('back', 'Back', reverse_lazy('index'))

    .. note:: The first argument is also slugified and turned into the id for
              the submit button.
    """
    template = "bootstrap/layout/linkbutton.html"
    field_classes = 'btn'

    def __init__(self, name, text, url, *args, **kwargs):
        self.href = url
        super(LinkButton, self).__init__(name, text, *args, **kwargs)


class BlacklistForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        Div(
            Row(
                Div(
                    Fieldset(
                        'Blacklist detail',
                        'ipv4',
                        'host',
                        'reason',
                        'type',
                    ),
                    css_class='span8'),
                Div(
                    HTML('<p>hello</p>'),
                    css_class='span4'),
            ),
            ButtonHolder(
                Submit('submit', 'Save'),
                LinkButton('back', 'Back', reverse_lazy(
                    'network.domain_list'))
            ),
            css_class="form-horizontal"))

    class Meta:
        model = Blacklist


class DomainForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        Div(
            Row(
                Div(
                    Fieldset(
                        'Identity',
                        'name',
                        'owner',
                        'ttl',
                    ),
                    css_class='span8'),
                Div(
                    HTML('<p>hello</p>'),
                    css_class='span4'),
            ),
            ButtonHolder(
                Submit('submit', 'Save'),
                LinkButton('back', 'Back', reverse_lazy(
                    'network.domain_list'))
            ),
            css_class="form-horizontal"))

    class Meta:
        model = Domain


class GroupForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        Div(
            Row(
                Div(
                    Fieldset(
                        'Identity',
                        'name',
                        'description',
                        'owner',
                    ),
                    css_class='span8'),
                Div(
                    HTML('<p>hello</p>'),
                    css_class='span4'),
            ),
            ButtonHolder(
                Submit('submit', 'Save'),
                LinkButton('back', 'Back', reverse_lazy(
                    'network.group_list'))
            ),
            css_class="form-horizontal"))

    class Meta:
        model = Group


class HostForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        Div(
            Row(
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
                        'Info',
                        'description',
                        'location',
                        'comment',
                        'owner',
                        # 'created_at',
                        # 'modified_at',
                        # 'id'
                    ),
                    css_class='span12'),
            ),
            ButtonHolder(
                Submit('submit', 'Save'),
                LinkButton('back', 'Back', reverse_lazy(
                    'network.host_list'))
            ),
            css_class="form-horizontal"))

    class Meta:
        model = Host


class RecordForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        Div(
            Row(
                Div(
                    Fieldset(
                        'Identity',
                        'name',
                        'domain',
                        'type',
                        'address',
                        'ttl',
                        'host',
                        'description',
                        'owner',
                    ),
                    css_class='span8'),
                Div(
                    HTML('<p>hello</p>'),
                    css_class='span4'),
            ),
            ButtonHolder(
                Submit('submit', 'Save'),
                LinkButton('back', 'Back', reverse_lazy(
                    'network.record_list'))
            ),
            css_class="form-horizontal"))

    class Meta:
        model = Record


class RuleForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        Div(
            Row(
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
                        'r_type',
                        'nat',
                        'nat_dport',
                    ),
                    Fieldset(
                        'External',
                        'vlan',
                        'vlangroup',
                        'host',
                        'hostgroup',
                        'firewall'
                    ),
                    css_class='span8'),
                Div(
                    HTML('<p>hello</p>'),
                    css_class='span4'),
            ),
            ButtonHolder(
                Submit('submit', 'Save'),
                LinkButton('back', 'Back', reverse_lazy(
                    'network.rule_list'))
            ),
            css_class="form-horizontal"))

    class Meta:
        model = Rule


class VlanForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        Div(
            Row(
                Fieldset(
                    'Identity',
                    'name',
                    'vid',
                    'interface',
                ),
                Fieldset(
                    'IPv4',
                    'net4',
                    'prefix4',
                    'ipv4',
                    'snat_to',
                    'snat_ip',
                    'dhcp_pool',
                ),
                Fieldset(
                    'IPv6',
                    'net6',
                    'prefix6',
                    'ipv6',
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
            ButtonHolder(
                Submit('submit', 'Save'),
                LinkButton('back', 'Back', reverse_lazy(
                    'network.host_list'))
            ),
            css_class="form-horizontal"))

    class Meta:
        model = Vlan


class VlanGroupForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        Div(
            Row(
                Fieldset(
                    'Identity',
                    'name',
                    'vlans',
                    'description',
                    'owner',
                ),
            ),
            ButtonHolder(
                Submit('submit', 'Save'),
                LinkButton('back', 'Back', reverse_lazy(
                    'network.vlan_group_list'))
            ),
            css_class="form-horizontal"))

    class Meta:
        model = VlanGroup
