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
from django.forms import (
    ModelForm, ModelChoiceField, ChoiceField, Form, CharField, RadioSelect,
)
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.template import RequestContext
from django.template.loader import render_to_string

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from request.models import (
    LeaseType, TemplateAccessType, TemplateAccessAction,
)
from dashboard.forms import VmResourcesForm


class LeaseTypeForm(ModelForm):
    @property
    def helper(self):
        helper = FormHelper()
        helper.add_input(Submit("submit", _("Save"),
                                css_class="btn btn-success", ))
        return helper

    class Meta:
        model = LeaseType


class TemplateAccessTypeForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(TemplateAccessTypeForm, self).__init__(*args, **kwargs)

    @property
    def helper(self):
        helper = FormHelper()
        helper.add_input(Submit("submit", _("Save"),
                                css_class="btn btn-success", ))
        return helper

    class Meta:
        model = TemplateAccessType


class InitialFromFileMixin(object):
    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request", None)
        super(InitialFromFileMixin, self).__init__(*args, **kwargs)

        self.initial['message'] = render_to_string(
            self.initial_template,
            RequestContext(request, {}),
        )


class TemplateRequestForm(InitialFromFileMixin, Form):
    template = ModelChoiceField(TemplateAccessType.objects.all(),
                                label=_("Template share"))
    level = ChoiceField(TemplateAccessAction.LEVELS, widget=RadioSelect,
                        initial=TemplateAccessAction.LEVELS.user)
    message = CharField(widget=forms.Textarea, label=_("Message"))

    initial_template = "request/initials/template.html"


class LeaseRequestForm(InitialFromFileMixin, Form):
    lease = ModelChoiceField(LeaseType.objects.all(), label=_("Lease"))
    message = CharField(widget=forms.Textarea)

    initial_template = "request/initials/lease.html"


class ResourceRequestForm(InitialFromFileMixin, VmResourcesForm):
    message = CharField(widget=forms.Textarea)

    initial_template = "request/initials/resources.html"
