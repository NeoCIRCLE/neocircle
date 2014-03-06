from datetime import timedelta
import uuid

from django.contrib.auth.models import User
from django.contrib.auth.forms import (
    AuthenticationForm, PasswordResetForm, SetPasswordForm,
)

from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
    Layout, Div, BaseInput, Field, HTML, Submit, Fieldset, TEMPLATE_PACK
)
from crispy_forms.utils import render_field
from django import forms
from django.forms.widgets import TextInput
from django.template import Context
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _
from sizefield.widgets import FileSizeWidget

from firewall.models import Vlan, Host
from storage.models import Disk, DataStore
from vm.models import InstanceTemplate, Lease, InterfaceTemplate, Node

VLANS = Vlan.objects.all()
DISKS = Disk.objects.exclude(type="qcow2-snap")


class VmCustomizeForm(forms.Form):
    name = forms.CharField()
    cpu_priority = forms.IntegerField()
    cpu_count = forms.IntegerField()
    ram_size = forms.IntegerField()

    disks = forms.ModelMultipleChoiceField(
        queryset=None, required=True)
    networks = forms.ModelMultipleChoiceField(
        queryset=None, required=False)

    template = forms.CharField()
    customized = forms.CharField()  # dummy flag field

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        self.template = kwargs.pop("template", None)
        super(VmCustomizeForm, self).__init__(*args, **kwargs)

        # set displayed disk and network list
        self.fields['disks'].queryset = Disk.get_objects_with_level(
            'user', self.user).exclude(type="qcow2-snap")
        self.fields['networks'].queryset = Vlan.get_objects_with_level(
            'user', self.user)

        # set initial for disk and network list
        self.initial['disks'] = self.template.disks.all()
        self.initial['networks'] = InterfaceTemplate.objects.filter(
            template=self.template).values_list("vlan", flat=True)

        # set initial for resources
        self.initial['cpu_priority'] = self.template.priority
        self.initial['cpu_count'] = self.template.num_cores
        self.initial['ram_size'] = self.template.ram_size

        # initial name and template pk
        self.initial['name'] = self.template.name
        self.initial['template'] = self.template.pk
        self.initial['customized'] = self.template.pk

        self.helper = FormHelper(self)
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            Field("template", type="hidden"),
            Field("customized", type="hidden"),
            Div(  # buttons
                Div(
                    AnyTag(  # tip: don't try to use Button class
                        "button",
                        AnyTag(
                            "i",
                            css_class="icon-play"
                        ),
                        HTML(" Start"),
                        css_id="vm-create-customized-start",
                        css_class="btn btn-success",

                    ),
                    css_class="col-sm-11 text-right",
                ),
                css_class="row",
            ),
            Div(
                Div(
                    Field("name"),
                    css_class="col-sm-5",
                ),
                css_class="row",
            ),
            Div(
                Div(
                    AnyTag(
                        'h2',
                        HTML(_("Resources")),
                    ),
                    css_class="col-sm-12",
                ),
                css_class="row",
            ),
            Div(  # cpu priority
                Div(
                    HTML('<label for="vm-cpu-priority-slider">'
                         '<i class="icon-trophy"></i> CPU priority'
                         '</label>'),
                    css_class="col-sm-3"
                ),
                Div(
                    Field('cpu_priority', id="vm-cpu-priority-slider",
                          css_class="vm-slider",
                          data_slider_min="0", data_slider_max="100",
                          data_slider_step="1",
                          data_slider_value=self.template.priority,
                          data_slider_handle="square",
                          data_slider_tooltip="hide"),
                    css_class="col-sm-9"
                ),
                css_class="row"
            ),
            Div(  # cpu count
                Div(
                    HTML('<label for="cpu-count-slider">'
                         '<i class="icon-cogs"></i> CPU count'
                         '</label>'),
                    css_class="col-sm-3"
                ),
                Div(
                    Field('cpu_count', id="vm-cpu-count-slider",
                          css_class="vm-slider",
                          data_slider_min="1", data_slider_max="8",
                          data_slider_step="1",
                          data_slider_value=self.template.num_cores,
                          data_slider_handle="square",
                          data_slider_tooltip="hide"),
                    css_class="col-sm-9"
                ),
                css_class="row"
            ),
            Div(  # ram size
                Div(
                    HTML('<label for="ram-slider">'
                         '<i class="icon-ticket"></i> RAM amount'
                         '</label>'),
                    css_class="col-sm-3"
                ),
                Div(
                    Field('ram_size', id="vm-ram-size-slider",
                          css_class="vm-slider",
                          data_slider_min="128", data_slider_max="4096",
                          data_slider_step="128",
                          data_slider_value=self.template.ram_size,
                          data_slider_handle="square",
                          data_slider_tooltip="hide"),
                    css_class="col-sm-9"
                ),
                css_class="row"
            ),
            Div(  # disks
                Div(
                    AnyTag(
                        "h2",
                        HTML("Disks")
                    ),
                    css_class="col-sm-4",
                ),
                Div(
                    Div(
                        Field("disks", css_class="form-control",
                              id="vm-create-disk-add-form"),
                        css_class="js-hidden",
                        style="padding-top: 15px; max-width: 450px;",
                    ),
                    Div(
                        AnyTag(
                            "h3",
                            HTML(_("No disks are added!")),
                            css_id="vm-create-disk-list",
                        ),
                        AnyTag(
                            "h3",
                            Div(
                                AnyTag(
                                    "select",
                                    css_class="form-control",
                                    css_id="vm-create-disk-add-select",
                                ),
                                Div(
                                    AnyTag(
                                        "a",
                                        AnyTag(
                                            "i",
                                            css_class="icon-plus-sign",
                                        ),
                                        href="#",
                                        css_id="vm-create-disk-add-button",
                                        css_class="btn btn-success",
                                    ),
                                    css_class="input-group-btn"
                                ),
                                css_class="input-group",
                                style="max-width: 330px;",
                            ),
                            css_id="vm-create-disk-add",
                        ),
                        css_class="no-js-hidden",
                    ),
                    css_class="col-sm-8",
                    style="padding-top: 3px;",
                ),
                css_class="row",
            ),  # end of disks
            Div(  # network
                Div(
                    AnyTag(
                        "h2",
                        HTML(_("Network")),
                    ),
                    css_class="col-sm-4",
                ),
                Div(
                    Div(  # js-hidden
                        Field(
                            "networks",
                            css_class="form-control",
                            id="vm-create-network-add-vlan",
                        ),
                        css_class="js-hidden",
                        style="padding-top: 15px; max-width: 450px;",
                    ),
                    Div(  # no-js-hidden
                        AnyTag(
                            "h3",
                            HTML(_("Not added to any network!")),
                            css_id="vm-create-network-list",
                        ),
                        AnyTag(
                            "h3",
                            Div(
                                AnyTag(
                                    "select",
                                    css_class=("form-control "
                                               "font-awesome-font"),
                                    css_id="vm-create-network-add-select",
                                ),
                                Div(
                                    AnyTag(
                                        "a",
                                        AnyTag(
                                            "i",
                                            css_class="icon-plus-sign",
                                        ),
                                        css_id=("vm-create-network-add"
                                                "-button"),
                                        css_class="btn btn-success",
                                    ),
                                    css_class="input-group-btn",
                                ),
                                css_class="input-group",
                                style="max-width: 330px;",
                            ),
                            css_class="vm-create-network-add"
                        ),
                        css_class="no-js-hidden",
                    ),
                    css_class="col-sm-8",
                    style="padding-top: 3px;",
                ),
                css_class="row"
            ),  # end of network
        )


class HostForm(forms.ModelForm):

    def setowner(self, user):
        self.instance.owner = user

    def __init__(self, *args, **kwargs):
        super(HostForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_show_labels = False
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                Div(  # host
                    Div(
                        AnyTag(
                            'h3',
                            HTML(_("Host")),
                        ),
                        css_class="col-sm-3",
                    ),
                    css_class="row",
                ),
                Div(  # host data
                    Div(  # hostname
                        HTML('<label for="node-hostname-box">'
                             'Name'
                             '</label>'),
                        css_class="col-sm-3",
                    ),
                    Div(  # hostname
                        'hostname',
                        css_class="col-sm-9",
                    ),
                    Div(  # mac
                        HTML('<label for="node-mac-box">'
                             'MAC'
                             '</label>'),
                        css_class="col-sm-3",
                    ),
                    Div(
                        'mac',
                        css_class="col-sm-9",
                    ),
                    Div(  # ip
                        HTML('<label for="node-ip-box">'
                             'IP'
                             '</label>'),
                        css_class="col-sm-3",
                    ),
                    Div(
                        'ipv4',
                        css_class="col-sm-9",
                    ),
                    Div(  # vlan
                        HTML('<label for="node-vlan-box">'
                             'VLAN'
                             '</label>'),
                        css_class="col-sm-3",
                    ),
                    Div(
                        'vlan',
                        css_class="col-sm-9",
                    ),
                    css_class="row",
                ),
            ),
        )

    class Meta:
        model = Host
        fields = ['hostname', 'vlan', 'mac', 'ipv4', ]


class NodeForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(NodeForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            Div(
                Div(
                    Div(
                        Div(
                            AnyTag(
                                'h3',
                                HTML(_("Node")),
                            ),
                            css_class="col-sm-3",
                        ),
                        css_class="row",
                    ),
                    Div(
                        Div(  # nodename
                            HTML('<label for="node-nodename-box">'
                                 'Name'
                                 '</label>'),
                            css_class="col-sm-3",
                        ),
                        Div(
                            'name',
                            css_class="col-sm-9",
                        ),
                        css_class="row",
                    ),
                    Div(
                        Div(  # priority
                            HTML('<label for="node-nodename-box">'
                                 'Priority'
                                 '</label>'),
                            css_class="col-sm-3",
                        ),
                        Div(
                            'priority',
                            css_class="col-sm-9",
                        ),
                        css_class="row",
                    ),
                    Div(
                        Div(  # enabled
                            HTML('<label for="node-nodename-box">'
                                 'Enabled'
                                 '</label>'),
                            css_class="col-sm-3",
                        ),
                        Div(
                            'enabled',
                            css_class="col-sm-9",
                        ),
                        css_class="row",
                    ),
                    Div(  # nested host
                        HTML("""{% load crispy_forms_tags %}
                            {% crispy hostform %}
                            """)
                    ),
                    Div(
                        Div(
                            AnyTag(  # tip: don't try to use Button class
                                "button",
                                AnyTag(
                                    "i",
                                    css_class="icon-play"
                                ),
                                HTML("Start"),
                                css_id="node-create-submit",
                                css_class="btn btn-success",
                            ),
                            css_class="col-sm-12 text-right",
                        ),
                        css_class="row",
                    ),
                    css_class="col-sm-11",
                ),
                css_class="row",
            ),
        )

    class Meta:
        model = Node
        fields = ['name', 'priority', 'enabled', ]


class TemplateForm(forms.ModelForm):
    networks = forms.ModelMultipleChoiceField(
        queryset=VLANS, required=False)

    def __init__(self, *args, **kwargs):
        parent = kwargs.pop("parent", None)
        self.user = kwargs.pop("user", None)
        super(TemplateForm, self).__init__(*args, **kwargs)
        self.fields['disks'] = forms.ModelMultipleChoiceField(
            queryset=Disk.get_objects_with_level(
                'user', self.user).exclude(type="qcow2-snap")
        )

        data = self.data.copy()
        data['owner'] = self.user.pk
        self.data = data

        if parent is not None:
            template = InstanceTemplate.objects.get(pk=parent)
            parent = template.__dict__
            fields = ["system", "name", "num_cores", "boot_menu", "ram_size",
                      "priority", "access_method", "raw_data",
                      "arch", "description"]
            for f in fields:
                self.initial[f] = parent[f]
            self.initial['lease'] = parent['lease_id']
            self.initial['disks'] = template.disks.all()
            self.initial['parent'] = template
            self.initial['name'] = "Clone of %s" % self.initial['name']
            self.for_networks = template
        else:
            self.for_networks = self.instance

        if self.instance.pk or parent is not None:
            n = self.for_networks.interface_set.values_list("vlan", flat=True)
            self.initial['networks'] = n

        if not self.instance.pk and len(self.errors) < 1:
            self.instance.priority = 20
            self.instance.ram_size = 512
            self.instance.num_cores = 2

    def clean_owner(self):
        if self.instance.pk is not None:
            return User.objects.get(pk=self.instance.owner.pk)
        return self.user

    def save(self, commit=True):
        data = self.cleaned_data
        self.instance.max_ram_size = data.get('ram_size')

        instance = super(TemplateForm, self).save(commit=False)
        if commit:
            instance.save()

        self.instance.disks = data['disks']  # TODO why do I need this

        # create and/or delete InterfaceTemplates
        networks = InterfaceTemplate.objects.filter(
            template=self.instance).values_list("vlan", flat=True)
        for m in data['networks']:
            if m.pk not in networks:
                InterfaceTemplate(vlan=m, managed=m.managed,
                                  template=self.instance).save()
        InterfaceTemplate.objects.filter(
            template=self.instance).exclude(
            vlan__in=data['networks']).delete()

        return instance

    @property
    def helper(self):
        kwargs_raw_data = {}
        if not self.user.is_superuser:
            kwargs_raw_data['readonly'] = None
        helper = FormHelper()
        helper.layout = Layout(
            Field("name"),
            Fieldset(
                _("Resource configuration"),
                Div(  # cpu count
                    Div(
                        Field('num_cores', id="vm-cpu-count-slider",
                              css_class="vm-slider",
                              data_slider_min="1", data_slider_max="8",
                              data_slider_step="1",
                              data_slider_value=self.instance.num_cores,
                              data_slider_handle="square",
                              data_slider_tooltip="hide"),
                        css_class="col-sm-9"
                    ),
                    css_class="row"
                ),
                Div(  # cpu priority
                    Div(
                        Field('priority', id="vm-cpu-priority-slider",
                              css_class="vm-slider",
                              data_slider_min="0", data_slider_max="100",
                              data_slider_step="1",
                              data_slider_value=self.instance.priority,
                              data_slider_handle="square",
                              data_slider_tooltip="hide"),
                        css_class="col-sm-9"
                    ),
                    css_class="row"
                ),
                Div(
                    Div(
                        Field('ram_size', id="vm-ram-size-slider",
                              css_class="vm-slider",
                              data_slider_min="128", data_slider_max="4096",
                              data_slider_step="128",
                              data_slider_value=self.instance.ram_size,
                              data_slider_handle="square",
                              data_slider_tooltip="hide"),
                        css_class="col-sm-9"
                    ),
                    css_class="row",
                ),
                Field('max_ram_size', type="hidden", value="0"),
                Field('arch'),
            ),
            Fieldset(
                "stuff",
                Field('access_method'),
                Field('boot_menu'),
                Field('raw_data', **kwargs_raw_data),
                Field('req_traits'),
                Field('description'),
                Field("parent", type="hidden"),
                Field("system"),
            ),
            Fieldset(
                _("Exeternal"),
                Field("disks"),
                Field("networks"),
                Field("lease"),
                Field("tags"),
            ),
        )
        helper.add_input(Submit('submit', 'Save changes'))
        return helper

    class Meta:
        model = InstanceTemplate
        exclude = ('state', )


class LeaseForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(LeaseForm, self).__init__(*args, **kwargs)
        self.generate_fields()

    # e2ae8b048e7198428f696375b8bdcd89e90002d1/django/utils/timesince.py#L10
    def get_intervals(self, delta_seconds):
        chunks = (
            (60 * 60 * 24 * 30, "months"),
            (60 * 60 * 24 * 7, "weeks"),
            (60 * 60 * 24, "days"),
            (60 * 60, "hours"),
        )
        for i, (seconds, name) in enumerate(chunks):
            count = delta_seconds // seconds
            if count != 0:
                break
        re = {'%s' % name: count}
        if i + 1 < len(chunks) and i > 0:
            seconds2, name2 = chunks[i + 1]
            count2 = (delta_seconds - (seconds * count)) // seconds2
            if count2 != 0:
                re['%s' % name2] = count2
        return re

    def generate_fields(self):
        intervals = ["hours", "days", "weeks", "months"]
        methods = ["suspend", "delete"]
        # feels redundant but these lines are so long
        s = (self.instance.suspend_interval.total_seconds()
             if self.instance.pk else 0)
        d = (self.instance.delete_interval.total_seconds()
             if self.instance.pk else 0)
        seconds = {
            'suspend': s,
            'delete': d
        }
        initial = {
            'suspend': self.get_intervals(int(seconds['suspend'])),
            'delete': self.get_intervals(int(seconds['delete']))
        }
        for m in methods:
            for idx, i in enumerate(intervals):
                self.fields["%s_%s" % (m, i)] = forms.IntegerField(
                    min_value=0, widget=NumberInput,
                    initial=initial[m].get(i, 0))

    def save(self, commit=True):
        data = self.cleaned_data

        suspend_seconds = timedelta(
            hours=data['suspend_hours'],
            days=(data['suspend_days'] + data['suspend_months'] % 12 * 30 +
                  data['suspend_months'] / 12 * 365),
            weeks=data['suspend_weeks'],
        )
        delete_seconds = timedelta(
            hours=data['delete_hours'],
            days=(data['delete_days'] + data['delete_months'] % 12 * 30 +
                  data['delete_months'] / 12 * 365),
            weeks=data['delete_weeks'],
        )
        self.instance.delete_interval = delete_seconds
        self.instance.suspend_interval = suspend_seconds
        instance = super(LeaseForm, self).save(commit=False)
        if commit:
            instance.save()
        return instance

    @property
    def helper(self):
        helper = FormHelper()
        helper.layout = Layout(
            Field('name'),
            Field("suspend_interval_seconds", type="hidden", value="0"),
            Field("delete_interval_seconds", type="hidden", value="0"),
            Div(
                Div(
                    HTML(_("Suspend in")),
                    css_class="input-group-addon",
                    style="width: 100px;",
                ),
                NumberField("suspend_hours", css_class="form-control"),
                Div(
                    HTML(_("hours")),
                    css_class="input-group-addon",
                ),
                NumberField("suspend_days", css_class="form-control"),
                Div(
                    HTML(_("days")),
                    css_class="input-group-addon",
                ),
                NumberField("suspend_weeks", css_class="form-control"),
                Div(
                    HTML(_("weeks")),
                    css_class="input-group-addon",
                ),
                NumberField("suspend_months", css_class="form-control"),
                Div(
                    HTML(_("months")),
                    css_class="input-group-addon",
                ),
                css_class="input-group interval-input",
            ),
            Div(
                Div(
                    HTML(_("Delete in")),
                    css_class="input-group-addon",
                    style="width: 100px;",
                ),
                NumberField("delete_hours", css_class="form-control"),
                Div(
                    HTML(_("hours")),
                    css_class="input-group-addon",
                ),
                NumberField("delete_days", css_class="form-control"),
                Div(
                    HTML(_("days")),
                    css_class="input-group-addon",
                ),
                NumberField("delete_weeks", css_class="form-control"),
                Div(
                    HTML(_("weeks")),
                    css_class="input-group-addon",
                ),
                NumberField("delete_months", css_class="form-control"),
                Div(
                    HTML(_("months")),
                    css_class="input-group-addon",
                ),
                css_class="input-group interval-input",
            )
        )
        helper.add_input(Submit("submit", "Save changes"))
        return helper

    class Meta:
        model = Lease


class DiskAddForm(forms.Form):
    name = forms.CharField()
    size = forms.CharField(widget=FileSizeWidget)

    def clean_size(self):
        size_in_bytes = self.cleaned_data.get("size")
        if not size_in_bytes.isdigit():
            raise forms.ValidationError(_("Invalid format, you can use "
                                          " GB or MB!"))
        return size_in_bytes

    def save(self, vm, commit=True):
        data = self.cleaned_data
        d = Disk(
            name=data['name'],
            filename=str(uuid.uuid4()),
            datastore=DataStore.objects.all()[0],
            type="qcow2-norm",
            size=data['size'],
            dev_num="a",
        )
        d.save()
        vm.disks.add(d)
        return d

    @property
    def helper(self):
        helper = FormHelper()
        helper.form_show_labels = False
        helper.layout = Layout(
            Field("name", placeholder=_("Name")),
            Field("size", placeholder=_("Disk size (for example: 20GB, "
                                        "1500MB)")),
        )
        helper.add_input(Submit("submit", "Create new disk",
                                css_class="btn btn-success"))
        return helper


class CircleAuthenticationForm(AuthenticationForm):
    # fields: username, password

    @property
    def helper(self):
        helper = FormHelper()
        helper.form_show_labels = False
        helper.layout = Layout(
            AnyTag(
                "div",
                AnyTag(
                    "span",
                    AnyTag(
                        "i",
                        css_class="icon-user",
                    ),
                    css_class="input-group-addon",
                ),
                Field("username", placeholder=_("Username"),
                      css_class="form-control"),
                css_class="input-group",
            ),
            AnyTag(
                "div",
                AnyTag(
                    "span",
                    AnyTag(
                        "i",
                        css_class="icon-lock",
                    ),
                    css_class="input-group-addon",
                ),
                Field("password", placeholder=_("Password"),
                      css_class="form-control"),
                css_class="input-group",
            ),
        )
        helper.add_input(Submit("submit", _("Sign in"),
                                css_class="btn btn-success"))
        return helper


class CirclePasswordResetForm(PasswordResetForm):
    # fields: email

    @property
    def helper(self):
        helper = FormHelper()
        helper.form_show_labels = False
        helper.layout = Layout(
            AnyTag(
                "div",
                AnyTag(
                    "span",
                    AnyTag(
                        "i",
                        css_class="icon-envelope",
                    ),
                    css_class="input-group-addon",
                ),
                Field("email", placeholder=_("Email address"),
                      css_class="form-control"),
                Div(
                    AnyTag(
                        "button",
                        HTML(_("Reset password")),
                        css_class="btn btn-success",
                    ),
                    css_class="input-group-btn",
                ),
                css_class="input-group",
            ),
        )
        return helper


class CircleSetPasswordForm(SetPasswordForm):

    @property
    def helper(self):
        helper = FormHelper()
        helper.add_input(Submit("submit", _("Change password"),
                                css_class="btn btn-success change-password",
                                css_id="submit-password-button"))
        return helper


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


class NumberInput(TextInput):
    input_type = "number"


class NumberField(Field):
    template = "crispy_forms/numberfield.html"

    def __init__(self, *args, **kwargs):
        kwargs['min'] = 0
        super(NumberField, self).__init__(*args, **kwargs)


class AnyTag(Div):
    template = "crispy_forms/anytag.html"

    def __init__(self, tag, *fields, **kwargs):
        self.tag = tag
        super(AnyTag, self).__init__(*fields, **kwargs)

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        fields = ''
        for field in self.fields:
            fields += render_field(field, form, form_style, context,
                                   template_pack=template_pack)

        return render_to_string(self.template, Context({'tag': self,
                                                        'fields': fields}))


class WorkingBaseInput(BaseInput):

    def __init__(self, name, value, input_type="text", **kwargs):
        self.input_type = input_type
        self.field_classes = ""  # we need this for some reason
        super(WorkingBaseInput, self).__init__(name, value, **kwargs)
