from django import forms
from vm.models import InstanceTemplate, Lease
from storage.models import Disk
from firewall.models import Vlan
# from django.core.urlresolvers import reverse_lazy

from crispy_forms.helper import FormHelper
from crispy_forms.layout import (Layout, Div, BaseInput,
                                 Field, HTML, Submit)
from crispy_forms.layout import TEMPLATE_PACK
from crispy_forms.utils import render_field
from django.template import Context
from django.template.loader import render_to_string

from django.utils.translation import ugettext as _
# from crispy_forms.bootstrap import FormActions


VLANS = Vlan.objects.all()


class VmCreateForm(forms.Form):
    template = forms.ModelChoiceField(queryset=InstanceTemplate.objects.all(),
                                      empty_label="Select pls")
    cpu_priority = forms.IntegerField()
    cpu_count = forms.IntegerField()
    ram_size = forms.IntegerField()

    disks = forms.ModelMultipleChoiceField(
        queryset=Disk.objects.exclude(type="qcow2-snap"),
        required=False
    )

    managed_networks = forms.ModelMultipleChoiceField(
        queryset=VLANS, required=False)
    unmanaged_networks = forms.ModelMultipleChoiceField(
        queryset=VLANS, required=False)

    def __init__(self, *args, **kwargs):
        super(VmCreateForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            Div(
                Div(
                    Field('template', id="vm-create-template-select",
                          css_class="select form-control"),
                    css_class="col-sm-10",
                ),
                css_class="row",
            ),
            Div(  # buttons
                Div(
                    AnyTag(
                        "a",
                        HTML("%s " % _("Advanced")),
                        AnyTag(
                            "i",
                            css_class="vm-create-advanced-icon icon-caret-down"
                        ),
                        css_class="btn btn-info vm-create-advanced-btn",
                    ),
                    css_class="col-sm-5",
                ),
                Div(
                    AnyTag(  # tip: don't try to use Button class
                        "button",
                        AnyTag(
                            "i",
                            css_class="icon-play"
                        ),
                        HTML(" Start"),
                        css_id="vm-create-submit",
                        css_class="btn btn-success",

                    ),
                    css_class="col-sm-5 text-right",
                ),
                css_class="row",
            ),
            Div(  # vm-create-advanced
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
                              data_slider_step="1", data_slider_value="20",
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
                              data_slider_step="1", data_slider_value="2",
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
                              data_slider_step="128", data_slider_value="512",
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
                            AnyTag(
                                "h4",
                                HTML(_("Managed networks")),
                            ),
                            Field(
                                "managed_networks",
                                css_class="form-control",
                                id="vm-create-network-add-managed",
                            ),
                            AnyTag(
                                "h4",
                                HTML(_("Unmanaged networks")),
                            ),
                            Field(
                                "unmanaged_networks",
                                css_class="form-control",
                                id="vm-create-network-add-unmanaged",
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
                                        css_class="form-control",
                                        css_id="vm-create-network-add-select",
                                    ),
                                    AnyTag(
                                        "span",
                                        WorkingBaseInput(
                                            "",
                                            "",
                                            css_id=(
                                                "vm-create-network-add"
                                                "checkbox-managed"
                                            ),
                                            input_type="checkbox",
                                            title="",
                                            data_original_title=(
                                                _("Managed network?")
                                            ),
                                            checked="checked",
                                        ),
                                        css_class="input-group-addon",
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
                css_class="vm-create-advanced"
            ),
        )


class TemplateForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(TemplateForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Save changes'))

    class Meta:
        model = InstanceTemplate


class LeaseForm(forms.ModelForm):

    @property
    def helper(self):
        helper = FormHelper()
        helper.add_input(Submit("submit", "Save changes"))
        return helper

    class Meta:
        model = Lease


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
