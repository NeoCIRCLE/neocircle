from django.forms import ModelForm, ModelChoiceField, ChoiceField, Form, CharField
from django import forms
from django.utils.translation import ugettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from request.models import (
    Request, LeaseType, TemplateAccessType, TemplateAccessAction,
)


class LeaseTypeForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(LeaseTypeForm, self).__init__(*args, **kwargs)

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

from django.forms import RadioSelect

class TemplateRequestForm(Form):
    template = ModelChoiceField(TemplateAccessType.objects.all(),
                                label="Template share")
    level = ChoiceField(TemplateAccessAction.LEVELS, widget=RadioSelect,
                        initial=TemplateAccessAction.LEVELS.user)
    reason = CharField(widget=forms.Textarea)
