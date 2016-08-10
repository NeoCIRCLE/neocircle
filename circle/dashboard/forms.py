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

from __future__ import absolute_import

from datetime import timedelta
from urlparse import urlparse

import pyotp

from django.forms import ModelForm
from django.contrib.auth.forms import (
    AuthenticationForm, PasswordResetForm, SetPasswordForm,
    PasswordChangeForm,
)
from django.contrib.auth.models import User, Group
from django.core.validators import URLValidator
from django.core.exceptions import PermissionDenied, ValidationError

import autocomplete_light
from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
    Layout, Div, BaseInput, Field, HTML, Submit, TEMPLATE_PACK, Fieldset
)

from crispy_forms.utils import render_field
from crispy_forms.bootstrap import FormActions

from django import forms
from django.contrib.auth.forms import UserCreationForm as OrgUserCreationForm
from django.forms.widgets import TextInput, HiddenInput
from django.template import Context
from django.template.loader import render_to_string
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from sizefield.widgets import FileSizeWidget
from django.core.urlresolvers import reverse_lazy

from django_sshkey.models import UserKey
from firewall.models import Vlan, Host
from vm.models import (
    InstanceTemplate, Lease, InterfaceTemplate, Node, Trait, Instance
)
from storage.models import DataStore, Disk
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.models import Permission
from .models import Profile, GroupProfile, Message
from circle.settings.base import LANGUAGES, MAX_NODE_RAM
from django.utils.translation import string_concat

from .validators import domain_validator

from dashboard.models import ConnectCommand, create_profile

LANGUAGES_WITH_CODE = ((l[0], string_concat(l[1], " (", l[0], ")"))
                       for l in LANGUAGES)

priority_choices = (
    (10, _("idle")),
    (30, _("normal")),
    (80, _("server")),
    (100, _("realtime")),
)


class NoFormTagMixin(object):

    @property
    def helper(self):
        helper = FormHelper(self)
        helper.form_tag = False
        return helper


class OperationForm(NoFormTagMixin, forms.Form):
    pass


class VmSaveForm(OperationForm):
    name = forms.CharField(max_length=100, label=_('Name'),
                           help_text=_('Human readable name of template.'))

    def __init__(self, *args, **kwargs):
        default = kwargs.pop('default', None)
        clone = kwargs.pop('clone', False)
        super(VmSaveForm, self).__init__(*args, **kwargs)
        if default:
            self.fields['name'].initial = default
        if clone:
            self.fields["clone"] = forms.BooleanField(
                required=False, label=_("Clone template permissions"),
                help_text=_("Clone the access list of parent template. Useful "
                            "for updating a template."))


class VmCustomizeForm(forms.Form):
    name = forms.CharField(widget=forms.TextInput(attrs={
        'class': "form-control",
        'style': "max-width: 350px",
        'required': "",
    }))

    cpu_count = forms.IntegerField(widget=forms.NumberInput(attrs={
        'class': "form-control input-tags cpu-count-input",
        'min': 1,
        'max': 10,
        'required': "",
    }),
        min_value=1, max_value=10,
    )

    ram_size = forms.IntegerField(widget=forms.TextInput(attrs={
        'class': "form-control input-tags ram-input",
        'min': 128,
        'pattern': "\d+",
        'max': MAX_NODE_RAM,
        'step': 128,
        'required': "",
    }),
        min_value=128, max_value=MAX_NODE_RAM,
    )

    cpu_priority = forms.ChoiceField(
        priority_choices, widget=forms.Select(attrs={
            'class': "form-control input-tags cpu-priority-input",
        })
    )

    amount = forms.IntegerField(widget=forms.NumberInput(attrs={
        'class': "form-control",
        'min': "1",
        'style': "max-width: 60px",
        'required': "",
    }), initial=1, min_value=1)

    disks = forms.ModelMultipleChoiceField(
        queryset=None, required=False,
        widget=forms.SelectMultiple(attrs={
            'class': "form-control",
            'id': "vm-create-disk-add-form",
        })
    )
    networks = forms.ModelMultipleChoiceField(
        queryset=None, required=False,
        widget=forms.SelectMultiple(attrs={
            'class': "form-control",
            'id': "vm-create-network-add-vlan",
        })
    )

    template = forms.CharField(widget=forms.HiddenInput())
    customized = forms.CharField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        self.template = kwargs.pop("template", None)
        super(VmCustomizeForm, self).__init__(*args, **kwargs)

        if self.user.has_perm("vm.set_resources"):
            self.allowed_fields = tuple(self.fields.keys())
            # set displayed disk and network list
            self.fields['disks'].queryset = self.template.disks.all()
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

        else:
            self.allowed_fields = ("name", "template", "customized", )

        # initial name and template pk
        self.initial['name'] = self.template.name
        self.initial['template'] = self.template.pk
        self.initial['customized'] = True

    def _clean_fields(self):
        for name, field in self.fields.items():
            if name in self.allowed_fields:
                value = field.widget.value_from_datadict(
                    self.data, self.files, self.add_prefix(name))
                try:
                    value = field.clean(value)
                    self.cleaned_data[name] = value
                    if hasattr(self, 'clean_%s' % name):
                        value = getattr(self, 'clean_%s' % name)()
                        self.cleaned_data[name] = value
                except ValidationError as e:
                    self._errors[name] = self.error_class(e.messages)
                    if name in self.cleaned_data:
                        del self.cleaned_data[name]


class GroupCreateForm(NoFormTagMixin, forms.ModelForm):

    description = forms.CharField(label=_("Description"), required=False,
                                  widget=forms.Textarea(attrs={'rows': 3}))

    def __init__(self, *args, **kwargs):
        new_groups = kwargs.pop('new_groups', None)
        super(GroupCreateForm, self).__init__(*args, **kwargs)
        choices = [('', '--')]
        if new_groups:
            choices += [(g, g) for g in new_groups if len(g) <= 64]
        self.fields['org_id'] = forms.ChoiceField(
            # TRANSLATORS: directory like in LDAP
            choices=choices, required=False, label=_('Directory identifier'))
        if new_groups:
            self.fields['org_id'].help_text = _(
                "If you select an item here, the members of this directory "
                "group will be automatically added to the group at the time "
                "they log in. Please note that other users (those with "
                "permissions like yours) may also automatically become a "
                "group co-owner).")
        else:
            self.fields['org_id'].widget = HiddenInput()

    def save(self, commit=True):
        if not commit:
            raise AttributeError('Committing is mandatory.')
        group = super(GroupCreateForm, self).save()

        profile = group.profile
        # multiple blanks were not be unique unlike NULLs are
        profile.org_id = self.cleaned_data['org_id'] or None
        profile.description = self.cleaned_data['description']
        profile.save()

        return group

    @property
    def helper(self):
        helper = super(GroupCreateForm, self).helper
        helper.add_input(Submit("submit", _("Create")))
        return helper

    class Meta:
        model = Group
        fields = ('name', )


class GroupProfileUpdateForm(NoFormTagMixin, forms.ModelForm):

    def __init__(self, *args, **kwargs):
        new_groups = kwargs.pop('new_groups', None)
        superuser = kwargs.pop('superuser', False)
        super(GroupProfileUpdateForm, self).__init__(*args, **kwargs)
        if not superuser:
            choices = [('', '--')]
            if new_groups:
                choices += [(g, g) for g in new_groups if len(g) <= 64]
            self.fields['org_id'] = forms.ChoiceField(
                choices=choices, required=False,
                label=_('Directory identifier'))
            if not new_groups:
                self.fields['org_id'].widget = HiddenInput()
        self.fields['description'].widget = forms.Textarea(attrs={'rows': 3})

    @property
    def helper(self):
        helper = super(GroupProfileUpdateForm, self).helper
        helper.add_input(Submit("submit", _("Save")))
        return helper

    def save(self, commit=True):
        profile = super(GroupProfileUpdateForm, self).save(commit=False)
        profile.org_id = self.cleaned_data['org_id'] or None
        if commit:
            profile.save()
        return profile

    class Meta:
        model = GroupProfile
        fields = ('description', 'org_id')


class HostForm(NoFormTagMixin, forms.ModelForm):

    def setowner(self, user):
        self.instance.owner = user

    @property
    def helper(self):
        helper = super(HostForm, self).helper
        helper.form_show_labels = False
        helper.layout = Layout(
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
        return helper

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
                                    css_class="fa fa-play"
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
        queryset=None, required=False, label=_("Networks"))

    num_cores = forms.IntegerField(widget=forms.NumberInput(attrs={
        'class': "form-control input-tags cpu-count-input",
        'min': 1,
        'max': 10,
        'required': "",
    }),
        min_value=1, max_value=10,
    )

    ram_size = forms.IntegerField(widget=forms.NumberInput(attrs={
        'class': "form-control input-tags ram-input",
        'min': 128,
        'max': MAX_NODE_RAM,
        'step': 128,
        'required': "",
    }),
        min_value=128, max_value=MAX_NODE_RAM,
    )

    priority = forms.ChoiceField(priority_choices, widget=forms.Select(attrs={
        'class': "form-control input-tags cpu-priority-input",
    }))

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super(TemplateForm, self).__init__(*args, **kwargs)

        self.fields['networks'].queryset = Vlan.get_objects_with_level(
            'user', self.user)

        data = self.data.copy()
        data['owner'] = self.user.pk
        self.data = data

        if self.instance.pk:
            n = self.instance.interface_set.values_list("vlan", flat=True)
            self.initial['networks'] = n

        if self.instance.pk and not self.instance.has_level(self.user,
                                                            'owner'):
            self.allowed_fields = ()
        else:
            self.allowed_fields = (
                'name', 'access_method', 'description', 'system', 'tags',
                'arch', 'lease', 'has_agent')
        if (self.user.has_perm('vm.change_template_resources') or
                not self.instance.pk):
            self.allowed_fields += tuple(set(self.fields.keys()) -
                                         set(['raw_data']))
        if self.user.is_superuser:
            self.allowed_fields += ('raw_data', )
        for name, field in self.fields.items():
            if name not in self.allowed_fields:
                field.widget.attrs['disabled'] = 'disabled'

        if not self.instance.pk and len(self.errors) < 1:
            self.initial['num_cores'] = 1
            self.initial['priority'] = 10
            self.initial['ram_size'] = 512
            self.initial['max_ram_size'] = 512

        lease_queryset = (
            Lease.get_objects_with_level("operator", self.user).distinct() |
            Lease.objects.filter(pk=self.instance.lease_id).distinct())

        self.fields["lease"].queryset = lease_queryset

        self.fields['raw_data'].validators.append(domain_validator)

    def clean_owner(self):
        if self.instance.pk is not None:
            return User.objects.get(pk=self.instance.owner.pk)
        return self.user

    def clean_max_ram_size(self):
        return self.cleaned_data.get("ram_size", 0)

    def _clean_fields(self):
        try:
            old = InstanceTemplate.objects.get(pk=self.instance.pk)
        except InstanceTemplate.DoesNotExist:
            old = None
        for name, field in self.fields.items():
            if name in self.allowed_fields:
                value = field.widget.value_from_datadict(
                    self.data, self.files, self.add_prefix(name))
                try:
                    value = field.clean(value)
                    self.cleaned_data[name] = value
                    if hasattr(self, 'clean_%s' % name):
                        value = getattr(self, 'clean_%s' % name)()
                        self.cleaned_data[name] = value
                except ValidationError as e:
                    self._errors[name] = self.error_class(e.messages)
                    if name in self.cleaned_data:
                        del self.cleaned_data[name]
            elif old:
                if name == 'networks':
                    self.cleaned_data[name] = [
                        i.vlan for i in self.instance.interface_set.all()]
                else:
                    self.cleaned_data[name] = getattr(old, name)

        if "req_traits" not in self.allowed_fields:
            self.cleaned_data['req_traits'] = self.instance.req_traits.all()

    def save(self, commit=True):
        data = self.cleaned_data
        self.instance.max_ram_size = data.get('ram_size')

        instance = super(TemplateForm, self).save(commit=True)

        # create and/or delete InterfaceTemplates
        networks = InterfaceTemplate.objects.filter(
            template=self.instance).values_list("vlan", flat=True)
        for m in data['networks']:
            if not m.has_level(self.user, "user"):
                raise PermissionDenied()
            if m.pk not in networks:
                InterfaceTemplate(vlan=m, managed=m.managed,
                                  template=self.instance).save()
        InterfaceTemplate.objects.filter(
            template=self.instance).exclude(
            vlan__in=data['networks']).delete()

        return instance

    @property
    def helper(self):
        submit_kwargs = {}
        if self.instance.pk and not self.instance.has_level(self.user,
                                                            'owner'):
            submit_kwargs['disabled'] = None

        helper = FormHelper()
        return helper

    class Meta:
        model = InstanceTemplate
        exclude = ('state', 'disks', )
        widgets = {
            'system': forms.TextInput,
            'max_ram_size': forms.HiddenInput,
            'parent': forms.Select(attrs={'disabled': ""}),
        }


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
            HTML(string_concat("<label>", _("Suspend in"), "</label>")),
            Div(
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
            HTML(string_concat("<label>", _("Delete in"), "</label>")),
            Div(
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
        helper.add_input(Submit("submit", _("Save changes")))
        return helper

    class Meta:
        model = Lease
        exclude = ()


class VmRenewForm(OperationForm):

    force = forms.BooleanField(required=False, label=_(
        "Set expiration times even if they are shorter than "
        "the current value."))
    save = forms.BooleanField(required=False, label=_(
        "Save selected lease."))

    def __init__(self, *args, **kwargs):
        choices = kwargs.pop('choices')
        default = kwargs.pop('default')
        super(VmRenewForm, self).__init__(*args, **kwargs)

        self.fields['lease'] = forms.ModelChoiceField(
            queryset=choices, initial=default, required=False,
            empty_label=None, label=_('Length'))
        if len(choices) < 2:
            self.fields['lease'].widget = HiddenInput()
            self.fields['save'].widget = HiddenInput()


class VmMigrateForm(forms.Form):
    live_migration = forms.BooleanField(
        required=False, initial=True, label=_("Live migration"),
        help_text=_(
            "Live migration is a way of moving virtual machines between "
            "hosts with a service interruption of at most some seconds. "
            "Please note that it can take very long and cause "
            "much network traffic in case of busy machines."))

    def __init__(self, *args, **kwargs):
        choices = kwargs.pop('choices')
        default = kwargs.pop('default')
        super(VmMigrateForm, self).__init__(*args, **kwargs)

        self.fields['to_node'] = forms.ModelChoiceField(
            queryset=choices, initial=default, required=False,
            widget=forms.RadioSelect(), label=_("Node"))


class VmStateChangeForm(OperationForm):

    interrupt = forms.BooleanField(required=False, label=_(
        "Forcibly interrupt all running activities."),
        help_text=_("Set all activities to finished state, "
                    "but don't interrupt any tasks."))
    new_state = forms.ChoiceField(Instance.STATUS, label=_(
        "New status"))
    reset_node = forms.BooleanField(required=False, label=_("Reset node"))

    def __init__(self, *args, **kwargs):
        show_interrupt = kwargs.pop('show_interrupt')
        status = kwargs.pop('status')
        super(VmStateChangeForm, self).__init__(*args, **kwargs)

        if not show_interrupt:
            self.fields['interrupt'].widget = HiddenInput()
        self.fields['new_state'].initial = status


class RedeployForm(OperationForm):
    with_emergency_change_state = forms.BooleanField(
        required=False, initial=True, label=_("use emergency state change"))


class VmCreateDiskForm(OperationForm):
    name = forms.CharField(max_length=100, label=_("Name"))
    size = forms.CharField(
        widget=FileSizeWidget, initial=(10 << 30), label=_('Size'),
        help_text=_('Size of disk to create in bytes or with units '
                    'like MB or GB.'))

    def __init__(self, *args, **kwargs):
        default = kwargs.pop('default', None)
        super(VmCreateDiskForm, self).__init__(*args, **kwargs)
        if default:
            self.fields['name'].initial = default

    def clean_size(self):
        size_in_bytes = self.cleaned_data.get("size")
        if not size_in_bytes.isdigit() and len(size_in_bytes) > 0:
            raise forms.ValidationError(_("Invalid format, you can use "
                                          " GB or MB!"))
        return size_in_bytes


class VmDiskResizeForm(OperationForm):
    size = forms.CharField(
        widget=FileSizeWidget, initial=(10 << 30), label=_('Size'),
        help_text=_('Size to resize the disk in bytes or with units '
                    'like MB or GB.'))

    def __init__(self, *args, **kwargs):
        choices = kwargs.pop('choices')
        self.disk = kwargs.pop('default')

        super(VmDiskResizeForm, self).__init__(*args, **kwargs)

        self.fields['disk'] = forms.ModelChoiceField(
            queryset=choices, initial=self.disk, required=True,
            empty_label=None, label=_('Disk'))
        if self.disk:
            self.fields['disk'].widget = HiddenInput()
            self.fields['size'].initial += self.disk.size

    def clean(self):
        cleaned_data = super(VmDiskResizeForm, self).clean()
        size_in_bytes = self.cleaned_data.get("size")
        disk = self.cleaned_data.get('disk')
        if not size_in_bytes.isdigit() and len(size_in_bytes) > 0:
            raise forms.ValidationError(_("Invalid format, you can use "
                                          " GB or MB!"))
        if int(size_in_bytes) < int(disk.size):
            raise forms.ValidationError(_("Disk size must be greater than the "
                                        "actual size."))
        return cleaned_data

    @property
    def helper(self):
        helper = super(VmDiskResizeForm, self).helper
        if self.disk:
            helper.layout = Layout(
                HTML(_("<label>Disk:</label> %s") % escape(self.disk)),
                Field('disk'), Field('size'))
        return helper


class VmDiskRemoveForm(OperationForm):
    def __init__(self, *args, **kwargs):
        choices = kwargs.pop('choices')
        self.disk = kwargs.pop('default')

        super(VmDiskRemoveForm, self).__init__(*args, **kwargs)

        self.fields['disk'] = forms.ModelChoiceField(
            queryset=choices, initial=self.disk, required=True,
            empty_label=None, label=_('Disk'))
        if self.disk:
            self.fields['disk'].widget = HiddenInput()

    @property
    def helper(self):
        helper = super(VmDiskRemoveForm, self).helper
        if self.disk:
            helper.layout = Layout(
                AnyTag(
                    "div",
                    HTML(_("<label>Disk:</label> %s") % escape(self.disk)),
                    css_class="form-group",
                ),
                Field("disk"),
            )
        return helper


class VmDownloadDiskForm(OperationForm):
    name = forms.CharField(max_length=100, label=_("Name"), required=False)
    url = forms.CharField(label=_('URL'), validators=[URLValidator(), ])

    def clean(self):
        cleaned_data = super(VmDownloadDiskForm, self).clean()
        if not cleaned_data['name']:
            if cleaned_data.get('url'):
                cleaned_data['name'] = urlparse(
                    cleaned_data['url']).path.split('/')[-1]
            if not cleaned_data['name']:
                raise forms.ValidationError(
                    _("Could not find filename in URL, "
                      "please specify a name explicitly."))
        return cleaned_data


class VmRemoveInterfaceForm(OperationForm):
    def __init__(self, *args, **kwargs):
        choices = kwargs.pop('choices')
        self.interface = kwargs.pop('default')

        super(VmRemoveInterfaceForm, self).__init__(*args, **kwargs)

        self.fields['interface'] = forms.ModelChoiceField(
            queryset=choices, initial=self.interface, required=True,
            empty_label=None, label=_('Interface'))
        if self.interface:
            self.fields['interface'].widget = HiddenInput()

    @property
    def helper(self):
        helper = super(VmRemoveInterfaceForm, self).helper
        if self.interface:
            helper.layout = Layout(
                AnyTag(
                    "div",
                    HTML(format_html(
                        _("<label>Vlan:</label> {0}"),
                        self.interface.vlan)),
                    css_class="form-group",
                ),
                Field("interface"),
            )
        return helper


class VmAddInterfaceForm(OperationForm):
    def __init__(self, *args, **kwargs):
        choices = kwargs.pop('choices')
        super(VmAddInterfaceForm, self).__init__(*args, **kwargs)

        field = forms.ModelChoiceField(
            queryset=choices, required=True, label=_('Vlan'))
        if not choices:
            field.widget.attrs['disabled'] = 'disabled'
            field.empty_label = _('No more networks.')
        self.fields['vlan'] = field


class DeployChoiceField(forms.ModelChoiceField):
    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop("instance")
        super(DeployChoiceField, self).__init__(*args, **kwargs)

    def label_from_instance(self, obj):
        traits = set(obj.traits.all())
        req_traits = set(self.instance.req_traits.all())
        # if the subset is empty the node satisfies the required traits
        subset = req_traits - traits

        label = "%s %s" % (
            "&#xf071" if subset else "&#xf00c;", escape(obj.name),
        )

        if subset:
            missing_traits = ", ".join(map(lambda x: escape(x.name), subset))
            label += _(" (missing_traits: %s)") % missing_traits

        return mark_safe(label)


class VmDeployForm(OperationForm):

    def __init__(self, *args, **kwargs):
        choices = kwargs.pop('choices', None)
        instance = kwargs.pop('instance', None)

        super(VmDeployForm, self).__init__(*args, **kwargs)

        if choices is not None:
            self.fields['node'] = DeployChoiceField(
                queryset=choices, required=False, label=_('Node'), help_text=_(
                    "Deploy virtual machine to this node "
                    "(blank allows scheduling automatically)."),
                widget=forms.Select(attrs={
                    'class': "font-awesome-font",
                }), instance=instance
            )


class VmPortRemoveForm(OperationForm):
    def __init__(self, *args, **kwargs):
        choices = kwargs.pop('choices')
        self.rule = kwargs.pop('default')

        super(VmPortRemoveForm, self).__init__(*args, **kwargs)

        self.fields['rule'] = forms.ModelChoiceField(
            queryset=choices, initial=self.rule, required=True,
            empty_label=None, label=_('Port'))
        if self.rule:
            self.fields['rule'].widget = HiddenInput()


class VmPortAddForm(OperationForm):
    port = forms.IntegerField(required=True, label=_('Port'),
                              min_value=1, max_value=65535)
    proto = forms.ChoiceField((('tcp', 'tcp'), ('udp', 'udp')),
                              required=True, label=_('Protocol'))

    def __init__(self, *args, **kwargs):
        choices = kwargs.pop('choices')
        self.host = kwargs.pop('default')

        super(VmPortAddForm, self).__init__(*args, **kwargs)

        self.fields['host'] = forms.ModelChoiceField(
            queryset=choices, initial=self.host, required=True,
            empty_label=None, label=_('Host'))
        if self.host:
            self.fields['host'].widget = HiddenInput()

    @property
    def helper(self):
        helper = super(VmPortAddForm, self).helper
        if self.host:
            helper.layout = Layout(
                AnyTag(
                    "div",
                    HTML(format_html(
                        _("<label>Host:</label> {0}"), self.host)),
                    css_class="form-group",
                ),
                Field("host"),
                Field("proto"),
                Field("port"),
            )
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
                        css_class="fa fa-user",
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
                        css_class="fa fa-lock",
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
                        css_class="fa fa-envelope",
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


class TraitForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(TraitForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            Div(
                Field('name', id="node-details-traits-input",
                      css_class="input-sm input-traits"),
                Div(
                    Submit("submit", _("Add trait"),
                           css_class="btn btn-primary btn-sm input-traits"),
                    css_class="input-group-btn",
                ),
                css_class="input-group",
                id="node-details-traits-form",
            ),
        )

    class Meta:
        model = Trait
        fields = ['name']


class MyProfileForm(forms.ModelForm):
    preferred_language = forms.ChoiceField(
        LANGUAGES_WITH_CODE,
        label=_("Preferred language"),
    )

    class Meta:
        fields = ('preferred_language', 'email_notifications',
                  'desktop_notifications', 'use_gravatar', )
        model = Profile

    @property
    def helper(self):
        helper = FormHelper()
        helper.add_input(Submit("submit", _("Save")))
        return helper

    def save(self, *args, **kwargs):
        value = super(MyProfileForm, self).save(*args, **kwargs)
        return value


class UnsubscribeForm(forms.ModelForm):

    class Meta:
        fields = ('email_notifications', )
        model = Profile

    @property
    def helper(self):
        helper = FormHelper()
        helper.add_input(Submit("submit", _("Save")))
        return helper


class CirclePasswordChangeForm(PasswordChangeForm):

    @property
    def helper(self):
        helper = FormHelper()
        helper.add_input(Submit("submit", _("Change password"),
                                css_class="btn btn-primary",
                                css_id="submit-password-button"))
        return helper


class UserCreationForm(OrgUserCreationForm):
    def __init__(self, *args, **kwargs):
        choices = kwargs.pop('choices')
        group = kwargs.pop('default')

        super(UserCreationForm, self).__init__(*args, **kwargs)

        self.fields['groups'] = forms.ModelMultipleChoiceField(
            queryset=choices, initial=[group], required=False,
            label=_('Groups'))

    class Meta:
        model = User
        fields = ("username", 'email', 'first_name', 'last_name', 'groups')

    @property
    def helper(self):
        helper = FormHelper()
        helper.layout = Layout('username', 'password1', 'password2', 'email',
                               'first_name', 'last_name')
        helper.add_input(Submit("submit", _("Save")))
        return helper

    def save(self, commit=True):
        user = super(UserCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            create_profile(user)
            user.groups.add(*self.cleaned_data["groups"])
        return user


class UserEditForm(forms.ModelForm):
    instance_limit = forms.IntegerField(
        label=_('Instance limit'),
        min_value=0, widget=NumberInput)
    two_factor_secret = forms.CharField(
        label=_('Two-factor authentication secret'),
        help_text=_("Remove the secret key to disable two-factor "
                    "authentication for this user."), required=False)

    def __init__(self, *args, **kwargs):
        super(UserEditForm, self).__init__(*args, **kwargs)
        self.fields["instance_limit"].initial = (
            self.instance.profile.instance_limit)
        self.fields["two_factor_secret"].initial = (
            self.instance.profile.two_factor_secret)

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'instance_limit',
                  'is_active', "two_factor_secret", )

    def save(self, commit=True):
        user = super(UserEditForm, self).save()
        user.profile.instance_limit = (
            self.cleaned_data['instance_limit'] or None)
        user.profile.two_factor_secret = (
            self.cleaned_data['two_factor_secret'] or None)
        user.profile.save()
        return user

    @property
    def helper(self):
        helper = FormHelper()
        helper.add_input(Submit("submit", _("Save")))
        return helper


class AclUserOrGroupAddForm(forms.Form):
    name = forms.CharField(widget=autocomplete_light.TextWidget(
        'AclUserGroupAutocomplete',
        attrs={'class': 'form-control',
               'placeholder': _("Name of group or user")}))


class TransferOwnershipForm(forms.Form):
    name = forms.CharField(
        widget=autocomplete_light.TextWidget(
            'AclUserAutocomplete',
            attrs={'class': 'form-control',
                   'placeholder': _("Name of user")}),
        label=_("E-mail address or identifier of user"))


class AddGroupMemberForm(forms.Form):
    new_member = forms.CharField(
        widget=autocomplete_light.TextWidget(
            'AclUserAutocomplete',
            attrs={'class': 'form-control',
                   'placeholder': _("Name of user")}),
        label=_("E-mail address or identifier of user"))


class UserKeyForm(forms.ModelForm):
    name = forms.CharField(required=True, label=_('Name'))
    key = forms.CharField(
        label=_('Key'), required=True,
        help_text=_('For example: ssh-rsa AAAAB3NzaC1yc2ED...'),
        widget=forms.Textarea(attrs={'rows': 5}))

    class Meta:
        fields = ('name', 'key')
        model = UserKey

    @property
    def helper(self):
        helper = FormHelper()
        helper.add_input(Submit("submit", _("Save")))
        return helper

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super(UserKeyForm, self).__init__(*args, **kwargs)

    def clean(self):
        if self.user:
            self.instance.user = self.user
        return super(UserKeyForm, self).clean()


class ConnectCommandForm(forms.ModelForm):
    class Meta:
        fields = ('name', 'access_method', 'template')
        model = ConnectCommand

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super(ConnectCommandForm, self).__init__(*args, **kwargs)

    def clean(self):
        if self.user:
            self.instance.user = self.user

        return super(ConnectCommandForm, self).clean()


class TraitsForm(forms.ModelForm):

    class Meta:
        model = Instance
        fields = ('req_traits', )

    @property
    def helper(self):
        helper = FormHelper()
        helper.form_show_labels = False
        helper.form_action = reverse_lazy("dashboard.views.vm-traits",
                                          kwargs={'pk': self.instance.pk})
        helper.add_input(Submit("submit", _("Save"),
                                css_class="btn btn-success", ))
        return helper


class RawDataForm(forms.ModelForm):
    raw_data = forms.CharField(validators=[domain_validator],
                               widget=forms.Textarea(attrs={'rows': 5}),
                               required=False)

    class Meta:
        model = Instance
        fields = ('raw_data', )

    @property
    def helper(self):
        helper = FormHelper()
        helper.form_show_labels = False
        helper.form_action = reverse_lazy("dashboard.views.vm-raw-data",
                                          kwargs={'pk': self.instance.pk})
        helper.add_input(Submit("submit", _("Save"),
                                css_class="btn btn-success",
                                css_id="submit-password-button"))
        return helper


class GroupPermissionForm(forms.ModelForm):
    permissions = forms.ModelMultipleChoiceField(
        queryset=None,
        widget=FilteredSelectMultiple(_("permissions"), is_stacked=False)
    )

    def get_filtered_permissions(self):
        """ Collected with this + djcelery source
        def get_model_classes_in_module(module):
            import sys
            import inspect
            from django.db.models import Model
            classes = []
            for name, obj in inspect.getmembers(sys.modules[module]):
                if inspect.isclass(obj) and issubclass(obj, Model):
                    classes.append(name.lower())
            return classes
        """
        excluded_objs = [
            "tag", "taggeditem", "level", "objectlevel",
            "permission", "contenttype", "migrationhistory", "site",
            "session", "intervalschedule", "crontabschedule", "periodictask",
            "periodictasks", "workerstate", "taskstate", "taskmeta",
            "tasksetmeta", "logentry",
            "baseresourceconfigmodel", "instance", "instanceactivity",
            "instancetemplate", "interface", "interfacetemplate", "lease",
            "namedbaseresourceconfig", "node", "nodeactivity", "trait",
            "virtualmachinedescmodel", "aclbase", "connectcommand",
            "favourite", "futuremember", "groupprofile", "model",
            "notification", "profile", "timestampedmodel", "userkey",
            "datastore", "disk", "model", "timestampedmodel", "aclbase",
            "blacklistitem", "domain", "ethernetdevice", "firewall",
            "host", "record", "rule", "switchport",
            "vlan", "vlangroup", "sender",
        ]

        exclude_add = ["add_%s" % l for l in excluded_objs]
        exclude_change = ["change_%s" % l for l in excluded_objs]
        exclude_delete = ["delete_%s" % l for l in excluded_objs + ["user"]]
        return Permission.objects.exclude(codename__in=exclude_add).exclude(
            codename__in=exclude_change).exclude(codename__in=exclude_delete)

    def __init__(self, *args, **kwargs):
        super(GroupPermissionForm, self).__init__(*args, **kwargs)
        self.fields['permissions'].queryset = self.get_filtered_permissions()

    class Meta:
        model = Group
        fields = ('permissions', )

    @property
    def helper(self):
        helper = FormHelper()
        helper.form_show_labels = False
        helper.form_action = reverse_lazy(
            "dashboard.views.group-permissions",
            kwargs={'group_pk': self.instance.pk})
        helper.add_input(Submit("submit", _("Save"),
                                css_class="btn btn-success", ))
        return helper


class VmResourcesForm(forms.ModelForm):
    num_cores = forms.IntegerField(widget=forms.NumberInput(attrs={
        'class': "form-control input-tags cpu-count-input",
        'min': 1,
        'max': 10,
        'required': "",
    }),
        min_value=1, max_value=10,
    )

    ram_size = forms.IntegerField(widget=forms.NumberInput(attrs={
        'class': "form-control input-tags ram-input",
        'min': 128,
        'max': MAX_NODE_RAM,
        'step': 128,
        'required': "",
    }),
        min_value=128, max_value=MAX_NODE_RAM,
    )

    priority = forms.ChoiceField(priority_choices, widget=forms.Select(attrs={
        'class': "form-control input-tags cpu-priority-input",
    }))

    def __init__(self, *args, **kwargs):
        self.can_edit = kwargs.pop("can_edit", None)
        super(VmResourcesForm, self).__init__(*args, **kwargs)

        if not self.can_edit:
            for name, field in self.fields.items():
                field.widget.attrs['disabled'] = "disabled"

    class Meta:
        model = Instance
        fields = ('num_cores', 'priority', 'ram_size', )


vm_search_choices = (
    ("owned", _("owned")),
    ("shared", _("shared")),
    ("all", _("all")),
)


class VmListSearchForm(forms.Form):
    s = forms.CharField(widget=forms.TextInput(attrs={
        'class': "form-control input-tags",
        'placeholder': _("Search...")
    }))

    stype = forms.ChoiceField(vm_search_choices, widget=forms.Select(attrs={
        'class': "btn btn-default form-control input-tags",
        'style': "min-width: 80px;",
    }))

    include_deleted = forms.BooleanField(widget=forms.CheckboxInput(attrs={
        'id': "vm-list-search-checkbox",
    }))

    def __init__(self, *args, **kwargs):
        super(VmListSearchForm, self).__init__(*args, **kwargs)
        # set initial value, otherwise it would be overwritten by request.GET
        if not self.data.get("stype"):
            data = self.data.copy()
            data['stype'] = "all"
            self.data = data


class TemplateListSearchForm(forms.Form):
    s = forms.CharField(widget=forms.TextInput(attrs={
        'class': "form-control input-tags",
        'placeholder': _("Search...")
    }))

    stype = forms.ChoiceField(vm_search_choices, widget=forms.Select(attrs={
        'class': "btn btn-default input-tags",
    }))

    def __init__(self, *args, **kwargs):
        super(TemplateListSearchForm, self).__init__(*args, **kwargs)
        # set initial value, otherwise it would be overwritten by request.GET
        if not self.data.get("stype"):
            data = self.data.copy()
            data['stype'] = "owned"
            self.data = data


class UserListSearchForm(forms.Form):
    s = forms.CharField(widget=forms.TextInput(attrs={
        'class': "form-control input-tags",
        'placeholder': _("Search...")
    }))


class DataStoreForm(ModelForm):

    @property
    def helper(self):
        helper = FormHelper()
        helper.layout = Layout(
            Fieldset(
                '',
                'name',
                'path',
                'hostname',
            ),
            FormActions(
                Submit('submit', _('Save')),
            )
        )
        return helper

    class Meta:
        model = DataStore
        fields = ("name", "path", "hostname", )


class DiskForm(ModelForm):
    created = forms.DateTimeField()
    modified = forms.DateTimeField()

    def __init__(self, *args, **kwargs):
        super(DiskForm, self).__init__(*args, **kwargs)

        for k, v in self.fields.iteritems():
            v.widget.attrs['readonly'] = True
        self.fields['created'].initial = self.instance.created
        self.fields['modified'].initial = self.instance.modified

    class Meta:
        model = Disk
        fields = ("name", "filename", "datastore", "type", "bus", "size",
                  "base", "dev_num", "destroyed", "is_ready", )


class MessageForm(ModelForm):
    class Meta:
        model = Message
        fields = ("message", "enabled", "effect", "start", "end")
        help_texts = {
            'start': _("Start time of the message in "
                       "YYYY.DD.MM. hh.mm.ss format."),
            'end': _("End time of the message in "
                     "YYYY.DD.MM. hh.mm.ss format."),
            'effect': _('The color of the message box defined by the '
                        'respective '
                        '<a href="http://getbootstrap.com/components/#alerts">'
                        'Bootstrap class</a>.')
        }
        labels = {
            'start': _("Start time"),
            'end': _("End time")
        }

    @property
    def helper(self):
        helper = FormHelper()
        helper.add_input(Submit("submit", _("Save")))
        return helper


class TwoFactorForm(ModelForm):
    class Meta:
        model = Profile
        fields = ["two_factor_secret", ]


class TwoFactorConfirmationForm(forms.Form):
    confirmation_code = forms.CharField(
        label=_('Two-factor authentication passcode'),
        help_text=_("Get the code from your authenticator."))

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(TwoFactorConfirmationForm, self).__init__(*args, **kwargs)

    def clean_confirmation_code(self):
        totp = pyotp.TOTP(self.user.profile.two_factor_secret)
        if not totp.verify(self.cleaned_data.get('confirmation_code')):
            raise ValidationError(_("Invalid confirmation code."))
