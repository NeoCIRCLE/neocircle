from django.forms import ModelForm
from django.core.urlresolvers import reverse_lazy

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Row, HTML
from crispy_forms.layout import Div, ButtonHolder, Submit, BaseInput

from firewall.models import Host, Vlan


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
                        # 'created_at',
                        # 'modified_at',
                        # 'id'
                    ),
                    css_class='span8'),
                Div(
                    HTML('<p>hello</p>'),
                    css_class='span4'),
            ),
            ButtonHolder(
                Submit('submit', 'Save'),
                LinkButton('back', 'Back', reverse_lazy(
                    'network.host_list'))
            ),
            css_class="form-horizontal"))

    class Meta:
        model = Host


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
