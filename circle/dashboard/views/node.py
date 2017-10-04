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
from __future__ import unicode_literals, absolute_import

import json
from collections import OrderedDict

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse_lazy
from django.db.models import Count
from django.forms.models import inlineformset_factory
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _
from django.views.generic import DetailView, TemplateView, View

from braces.views import LoginRequiredMixin, SuperuserRequiredMixin
from django_tables2 import SingleTableView

from firewall.models import Host
from vm.models import Node, NodeActivity, Trait
from vm.tasks.vm_tasks import check_queue

from ..forms import TraitForm, HostForm, NodeForm
from ..tables import NodeListTable
from .util import AjaxOperationMixin, OperationView, GraphMixin, DeleteViewBase


def get_operations(instance, user):
    ops = []
    for k, v in node_ops.iteritems():
        try:
            op = v.get_op_by_object(instance)
            op.check_auth(user)
            op.check_precond()
        except Exception:
            ops.append(v.bind_to_object(instance, disabled=True))
        else:
            ops.append(v.bind_to_object(instance))
    return ops


class NodeOperationView(AjaxOperationMixin, OperationView):

    model = Node
    context_object_name = 'node'  # much simpler to mock object
    with_reload = True
    wait_for_result = None


node_ops = OrderedDict([
    ('activate', NodeOperationView.factory(
        op='activate', icon='play-circle', effect='success')),
    ('passivate', NodeOperationView.factory(
        op='passivate', icon='play-circle-o', effect='info')),
    ('disable', NodeOperationView.factory(
        op='disable', icon='times-circle-o', effect='danger')),
    ('update_node', NodeOperationView.factory(
        op='update_node', icon='refresh', effect='warning')),
    ('reset', NodeOperationView.factory(
        op='reset', icon='stethoscope', effect='danger')),
    ('flush', NodeOperationView.factory(
        op='flush', icon='paint-brush', effect='danger')),
])


def _get_activity_icon(act):
    op = act.get_operation()
    if op and op.id in node_ops:
        return node_ops[op.id].icon
    else:
        return "cog"


def _format_activities(acts):
    for i in acts:
        i.icon = _get_activity_icon(i)
    return acts


class NodeDetailView(LoginRequiredMixin,
                     GraphMixin, DetailView):
    template_name = "dashboard/node-detail.html"
    model = Node
    form = None
    form_class = TraitForm

    def get(self, *args, **kwargs):
        if not self.request.user.has_perm('vm.view_statistics'):
            raise PermissionDenied()
        return super(NodeDetailView, self).get(*args, **kwargs)

    def get_context_data(self, form=None, **kwargs):
        if form is None:
            form = self.form_class()
        context = super(NodeDetailView, self).get_context_data(**kwargs)
        na = NodeActivity.objects.filter(
            node=self.object, parent=None
        ).order_by('-started').select_related()
        context['ops'] = get_operations(self.object, self.request.user)
        context['op'] = {i.op: i for i in context['ops']}
        context['show_show_all'] = len(na) > 10
        context['activities'] = _format_activities(na[:10])
        context['trait_form'] = form
        context['graphite_enabled'] = (
            settings.GRAPHITE_URL is not None)

        node_hostname = self.object.host.hostname
        context['queues'] = {
            'vmcelery.fast': check_queue(node_hostname, "vm", "fast"),
            'vmcelery.slow': check_queue(node_hostname, "vm", "slow"),
            'netcelery.fast': check_queue(node_hostname, "net", "fast"),
        }
        return context

    def post(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied()
        if request.POST.get('new_name'):
            return self.__set_name(request)
        if request.POST.get('to_remove'):
            return self.__remove_trait(request)
        return redirect(reverse_lazy("dashboard.views.node-detail",
                                     kwargs={'pk': self.get_object().pk}))

    def __set_name(self, request):
        self.object = self.get_object()
        new_name = request.POST.get("new_name")
        Node.objects.filter(pk=self.object.pk).update(
            **{'name': new_name})

        success_message = _("Node successfully renamed.")
        if request.is_ajax():
            response = {
                'message': success_message,
                'new_name': new_name,
                'node_pk': self.object.pk
            }
            return HttpResponse(
                json.dumps(response),
                content_type="application/json"
            )
        else:
            messages.success(request, success_message)
            return redirect(reverse_lazy("dashboard.views.node-detail",
                                         kwargs={'pk': self.object.pk}))

    def __remove_trait(self, request):
        try:
            to_remove = request.POST.get('to_remove')
            trait = Trait.objects.get(pk=to_remove)
            node = self.get_object()
            node.traits.remove(to_remove)

            if not trait.in_use:
                trait.delete()

            message = u"Success"
        except:  # note this won't really happen
            message = u"Not success"

        if request.is_ajax():
            return HttpResponse(
                json.dumps({'message': message}),
                content_type="application/json"
            )
        else:
            return redirect(node.get_absolute_url())


class NodeList(LoginRequiredMixin, GraphMixin, SingleTableView):
    template_name = "dashboard/node-list.html"
    table_class = NodeListTable
    table_pagination = False

    def get(self, *args, **kwargs):
        if not self.request.user.has_perm('vm.view_statistics'):
            raise PermissionDenied()
        if self.request.is_ajax():
            nodes = Node.objects.all()
            nodes = [{
                'name': i.name,
                'icon': i.get_status_icon(),
                'url': i.get_absolute_url(),
                'label': i.get_status_label(),
                'status': i.state.lower()} for i in nodes]

            return HttpResponse(
                json.dumps(list(nodes)),
                content_type="application/json",
            )
        else:
            return super(NodeList, self).get(*args, **kwargs)

    def get_queryset(self):
        return Node.objects.annotate(
            number_of_VMs=Count('instance_set')).select_related('host')


class NodeCreate(LoginRequiredMixin, SuperuserRequiredMixin, TemplateView):

    form_class = HostForm
    hostform = None

    formset_class = inlineformset_factory(Host, Node, form=NodeForm, extra=1)
    formset = None

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/_modal.html']
        else:
            return ['dashboard/nojs-wrapper.html']

    def get(self, request, hostform=None, formset=None, *args, **kwargs):
        if hostform is None:
            hostform = self.form_class()
        if formset is None:
            formset = self.formset_class(instance=Host())
        context = self.get_context_data(**kwargs)
        context.update({
            'template': 'dashboard/node-create.html',
            'box_title': _('Create a node'),
            'hostform': hostform,
            'formset': formset,

        })
        return self.render_to_response(context)

    # TODO handle not ajax posts
    def post(self, request, *args, **kwargs):
        if not self.request.user.is_authenticated():
            raise PermissionDenied()

        hostform = self.form_class(request.POST)
        formset = self.formset_class(request.POST, Host())
        if not hostform.is_valid():
            return self.get(request, hostform, formset, *args, **kwargs)
        hostform.setowner(request.user)
        savedform = hostform.save(commit=False)
        formset = self.formset_class(request.POST, instance=savedform)
        if not formset.is_valid():
            return self.get(request, hostform, formset, *args, **kwargs)

        savedform.save()
        nodemodel = formset.save()
        messages.success(request, _('Node successfully created.'))
        path = nodemodel[0].get_absolute_url()
        if request.is_ajax():
            return HttpResponse(json.dumps({'redirect': path}),
                                content_type="application/json")
        else:
            return redirect(path)


class NodeDelete(SuperuserRequiredMixin, DeleteViewBase):
    model = Node
    success_message = _("Node successfully deleted.")

    def check_auth(self):
        # SuperuserRequiredMixin
        pass

    def get_success_url(self):
        return reverse_lazy('dashboard.views.node-list')


class NodeAddTraitView(SuperuserRequiredMixin, DetailView):
    model = Node
    template_name = "dashboard/node-add-trait.html"

    def get_success_url(self):
        next = self.request.GET.get('next')
        if next:
            return next
        else:
            return self.object.get_absolute_url()

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = super(NodeAddTraitView, self).get_context_data(**kwargs)
        context['form'] = (TraitForm(self.request.POST) if self.request.POST
                           else TraitForm())
        return context

    def post(self, request, pk, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = context['form']
        if form.is_valid():
            node = self.object
            n = form.cleaned_data['name']
            trait, created = Trait.objects.get_or_create(name=n)
            node.traits.add(trait)
            success_message = _("Trait successfully added to node.")
            messages.success(request, success_message)
            return redirect(self.get_success_url())
        else:
            return self.get(self, request, pk, *args, **kwargs)


class NodeActivityView(LoginRequiredMixin, SuperuserRequiredMixin, View):
    def get(self, request, pk):
        show_all = request.GET.get("show_all", "false") == "true"
        node = Node.objects.get(pk=pk)

        activities = _format_activities(NodeActivity.objects.filter(
            node=node, parent=None).order_by('-started').select_related())

        show_show_all = len(activities) > 10
        if not show_all:
            activities = activities[:10]

        response = {
            'activities': render_to_string(
                "dashboard/node-detail/_activity-timeline.html",
                {
                    'activities': activities,
                    'show_show_all': show_show_all
                },
                request
            )
        }

        return HttpResponse(
            json.dumps(response),
            content_type="application/json"
        )


class NodeActivityDetail(LoginRequiredMixin, SuperuserRequiredMixin,
                         DetailView):
    model = NodeActivity
    context_object_name = 'nodeactivity'  # much simpler to mock object
    template_name = 'dashboard/nodeactivity_detail.html'

    def get_context_data(self, **kwargs):
        ctx = super(NodeActivityDetail, self).get_context_data(**kwargs)
        ctx['activities'] = _format_activities(NodeActivity.objects.filter(
            node=self.object.node, parent=None
        ).order_by('-started').select_related())
        ctx['icon'] = _get_activity_icon(self.object)
        return ctx
