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

from django.views.generic import (TemplateView, UpdateView, DeleteView,
                                  CreateView)
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import render, redirect
from django.http import HttpResponse

from django_tables2 import SingleTableView

from firewall.models import (Host, Vlan, Domain, Group, Record, BlacklistItem,
                             Rule, VlanGroup, SwitchPort, EthernetDevice)
from vm.models import Interface
from .tables import (HostTable, VlanTable, SmallHostTable, DomainTable,
                     GroupTable, RecordTable, BlacklistItemTable, RuleTable,
                     VlanGroupTable, SmallRuleTable, SmallGroupRuleTable,
                     SmallRecordTable, SwitchPortTable)
from .forms import (HostForm, VlanForm, DomainForm, GroupForm, RecordForm,
                    BlacklistItemForm, RuleForm, VlanGroupForm, SwitchPortForm)

from django.contrib import messages
from django.views.generic.edit import FormMixin
from django.utils.translation import ugettext_lazy as _
from braces.views import LoginRequiredMixin, SuperuserRequiredMixin
# from django.db.models import Q
from operator import itemgetter
from itertools import chain
import json
from dashboard.views import AclUpdateView
from dashboard.forms import AclUserAddForm


class SuccessMessageMixin(FormMixin):
    """
    Adds a success message on successful form submission.
    From django/contrib/messages/views.py@9a85ad89
    """
    success_message = ''

    def form_valid(self, form):
        response = super(SuccessMessageMixin, self).form_valid(form)
        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            messages.success(self.request, success_message)
        return response

    def get_success_message(self, cleaned_data):
        return self.success_message % cleaned_data


class IndexView(LoginRequiredMixin, SuperuserRequiredMixin, TemplateView):
    template_name = "network/index.html"

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)

        size = 13
        blacklists = BlacklistItem.objects.all().order_by(
            '-modified_at')[:size]
        domains = Domain.objects.all().order_by('-modified_at')[:size]
        groups = Group.objects.all().order_by('-modified_at')[:size]
        hosts = Host.objects.all().order_by('-modified_at')[:size]
        records = Record.objects.all().order_by('-modified_at')[:size]
        vlans = Vlan.objects.all().order_by('-modified_at')[:size]
        vlangroups = VlanGroup.objects.all().order_by('-modified_at')[:size]
        rules = Rule.objects.all().order_by('-modified_at')[:size]

        result_list = []
        for i in (sorted(chain(domains, groups, hosts, records, vlans,
                               vlangroups, rules),
                         key=lambda x: x.modified_at, reverse=True)[:size]):
            result_list.append(
                {
                    'class_name': unicode(i.__class__.__name__),
                    'modified_at': i.modified_at,
                    'created_at': i.created_at,
                    'name': unicode(i),
                    'link': i.get_absolute_url()
                })

        context['latest_blacklists'] = blacklists
        context['latest'] = result_list
        return context


class BlacklistList(LoginRequiredMixin, SuperuserRequiredMixin,
                    SingleTableView):
    model = BlacklistItem
    table_class = BlacklistItemTable
    template_name = "network/blacklist-list.html"
    table_pagination = False


class BlacklistDetail(LoginRequiredMixin, SuperuserRequiredMixin,
                      SuccessMessageMixin, UpdateView):
    model = BlacklistItem
    template_name = "network/blacklist-edit.html"
    form_class = BlacklistItemForm
    success_message = _(u'Successfully modified blacklist item'
                        '%(ipv4)s - %(type)s!')

    def get_success_url(self):
        if 'pk' in self.kwargs:
            return reverse_lazy('network.blacklist', kwargs=self.kwargs)

    def get_context_data(self, **kwargs):
        context = super(BlacklistDetail, self).get_context_data(**kwargs)
        context['blacklist_pk'] = self.object.pk
        return context


class BlacklistCreate(LoginRequiredMixin, SuperuserRequiredMixin,
                      SuccessMessageMixin, CreateView):
    model = BlacklistItem
    template_name = "network/blacklist-create.html"
    form_class = BlacklistItemForm
    success_message = _(u'Successfully created blacklist item '
                        '%(ipv4)s - %(type)s!')


class BlacklistDelete(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = BlacklistItem
    template_name = "network/confirm/base_delete.html"

    def get_context_data(self, **kwargs):
        """ display more information about the object """
        context = super(BlacklistDelete, self).get_context_data(**kwargs)
        if 'pk' in self.kwargs:
            to_delete = BlacklistItem.objects.get(pk=self.kwargs['pk'])
            context['object'] = "%s - %s - %s" % (to_delete.ipv4,
                                                  to_delete.reason,
                                                  to_delete.type)
            return context

    def get_success_url(self):
        next = self.request.POST.get('next')
        if next:
            return self.request.POST['next']
        else:
            return reverse_lazy('network.blacklist_list')


class DomainList(LoginRequiredMixin, SuperuserRequiredMixin, SingleTableView):
    model = Domain
    table_class = DomainTable
    template_name = "network/domain-list.html"
    table_pagination = False


class DomainDetail(LoginRequiredMixin, SuperuserRequiredMixin,
                   SuccessMessageMixin, UpdateView):
    model = Domain
    template_name = "network/domain-edit.html"
    form_class = DomainForm
    success_message = _(u'Successfully modified domain %(name)s!')

    def get_success_url(self):
        if 'pk' in self.kwargs:
            return reverse_lazy('network.domain', kwargs=self.kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(DomainDetail, self).get_context_data(**kwargs)
        self.object = self.get_object()
        context['domain_pk'] = self.object.pk

        q = Record.objects.filter(
            domain=self.object,
            host__in=Host.objects.filter(
                interface__in=Interface.objects.filter(
                    instance__destroyed_at=None)
            )
        )
        context['record_list'] = SmallRecordTable(q)
        return context


class DomainCreate(LoginRequiredMixin, SuperuserRequiredMixin,
                   SuccessMessageMixin, CreateView):
    model = Domain
    template_name = "network/domain-create.html"
    form_class = DomainForm
    success_message = _(u'Successfully created domain %(name)s!')


class DomainDelete(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = Domain
    template_name = "network/confirm/base_delete.html"

    def get_success_url(self):
        next = self.request.POST.get('next')
        if next:
            return self.request.POST['next']
        else:
            return reverse_lazy('network.domain_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        if unicode(self.object) != request.POST.get('confirm'):
            messages.error(request, _(u"Object name does not match!"))
            return self.get(request, *args, **kwargs)

        response = super(DomainDelete, self).delete(request, *args, **kwargs)
        messages.success(request, _(u"Domain successfully deleted!"))
        return response

    def get_context_data(self, **kwargs):
        context = super(DomainDelete, self).get_context_data(**kwargs)

        records_from_hosts = _(u'Records from hosts')
        deps = []
        # vlans
        vlans = Vlan.objects.filter(domain=self.object).all()
        if len(vlans) > 0:
            deps.append({
                'name': _('Vlans'),
                'data': vlans
            })

            # hosts
            hosts = Host.objects.filter(vlan__in=deps[0]['data'])
            if len(hosts) > 0:
                deps.append({
                    'name': _('Hosts'),
                    'data':  hosts
                })

                # records
                records = Record.objects.filter(
                    host__in=deps[1]['data']
                    # Q(domain=self.object) | (host__in=deps[1]['data'])
                )
                if len(records) > 0:
                    deps.append({
                        'name': records_from_hosts,
                        'data': records
                    })

        records = Record.objects.filter(domain=self.object)
        if len(records) > 0:
            # to filter out doubles (records from hosts and domains)
            indexes = map(itemgetter('name'), deps)
            n = indexes.index(records_from_hosts) if len(indexes) > 0 else 0
            deps.append({
                'name': u'Records only from the domain',
                'data': records.exclude(pk__in=deps[n]['data']) if n > 0
                else records
            })

        context['deps'] = deps
        context['confirmation'] = True
        return context


class GroupList(LoginRequiredMixin, SuperuserRequiredMixin, SingleTableView):
    model = Group
    table_class = GroupTable
    template_name = "network/group-list.html"
    table_pagination = False


class GroupCreate(LoginRequiredMixin, SuperuserRequiredMixin,
                  SuccessMessageMixin, CreateView):
    model = Group
    template_name = "network/group-create.html"
    form_class = GroupForm
    success_message = _(u'Successfully created host group %(name)s!')


class GroupDetail(LoginRequiredMixin, SuperuserRequiredMixin,
                  SuccessMessageMixin, UpdateView):
    model = Group
    template_name = "network/group-edit.html"
    form_class = GroupForm
    success_message = _(u'Successfully modified host group %(name)s!')

    def get_success_url(self):
        if 'pk' in self.kwargs:
            return reverse_lazy('network.group', kwargs=self.kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(GroupDetail, self).get_context_data(**kwargs)

        context['group_pk'] = self.object.pk

        # records
        q = Rule.objects.filter(hostgroup=self.object)
        context['rule_list'] = SmallRuleTable(q)
        return context


class GroupDelete(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = Group
    template_name = "network/confirm/base_delete.html"

    def get_success_url(self):
        next = self.request.POST.get('next')
        if next:
            return self.request.POST['next']
        else:
            return reverse_lazy('network.group_list')

    def get_context_data(self, *args, **kwargs):
        context = super(GroupDelete, self).get_context_data(**kwargs)
        context['group_pk'] = self.object.pk
        return context


class HostList(LoginRequiredMixin, SuperuserRequiredMixin, SingleTableView):
    model = Host
    table_class = HostTable
    template_name = "network/host-list.html"
    table_pagination = False

    def get_context_data(self, **kwargs):
        context = super(HostList, self).get_context_data(**kwargs)
        q = Vlan.objects.all().order_by("name")
        context['vlans'] = q
        return context

    def get_table_data(self):
        vlan_id = self.request.GET.get('vlan')
        if vlan_id:
            data = Host.objects.filter(vlan=vlan_id).select_related()
        else:
            data = Host.objects.select_related()
        return data


class HostDetail(LoginRequiredMixin, SuperuserRequiredMixin,
                 SuccessMessageMixin, UpdateView):
    model = Host
    template_name = "network/host-edit.html"
    form_class = HostForm
    success_message = _(u'Successfully modified host %(hostname)s!')

    def get(self, request, *args, **kwargs):
        if request.is_ajax():
            host = Host.objects.get(pk=kwargs['pk'])
            host = {
                'hostname': host.hostname,
                'ipv4': str(host.ipv4),
                'ipv6': str(host.ipv6),
                'fqdn': host.get_fqdn()
            }
            return HttpResponse(json.dumps(host),
                                content_type="application/json")
        else:
            self.object = self.get_object()
            return super(HostDetail, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        # this is usually not None (well, with curl and whatnot it can be)
        if pk:
            groups = Host.objects.get(pk=pk).groups.all()
            groups = [i.pk for i in groups]
            # request.POST is immutable
            post_copy = request.POST.copy()
            post_copy.setlist('groups', groups)
            request.POST = post_copy
            return super(HostDetail, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(HostDetail, self).get_context_data(**kwargs)
        # own rules
        q = Rule.objects.filter(host=self.object).all()
        context['rule_list'] = SmallRuleTable(q)

        # rules from host groups
        group_rule_list = []
        for group in self.object.groups.all():
            q = Rule.objects.filter(hostgroup=group).all()
            group_rule_list.append({
                'table': SmallGroupRuleTable(q),
                'name': unicode(group),
                'pk': group.pk
            })
        context['group_rule_list'] = group_rule_list

        # available groups
        rest = Group.objects.exclude(pk__in=self.object.groups.all()).all()
        context['not_used_groups'] = rest

        # set host pk (we need this for URL-s)
        context['host_pk'] = self.kwargs['pk']

        from network.tables import HostRecordsTable
        context['records_table'] = HostRecordsTable(
            Record.objects.filter(host=self.get_object()),
            request=self.request, template="django_tables2/table_no_page.html"
        )

        return context

    def get_success_url(self):
        if 'pk' in self.kwargs:
            return reverse_lazy('network.host', kwargs=self.kwargs)


class HostCreate(LoginRequiredMixin, SuperuserRequiredMixin,
                 SuccessMessageMixin, CreateView):
    model = Host
    template_name = "network/host-create.html"
    form_class = HostForm
    success_message = _(u'Successfully created host %(hostname)s!')


class HostDelete(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = Host
    template_name = "network/confirm/base_delete.html"

    def get_success_url(self):
        next = self.request.POST.get('next')
        if next:
            return self.request.POST['next']
        else:
            return reverse_lazy('network.host_list')

    def get_context_data(self, *args, **kwargs):
        context = super(HostDelete, self).get_context_data(**kwargs)

        deps = []
        records = Record.objects.filter(host=self.object).all()
        if records:
            deps.append({
                'name': _('Records'),
                'data': records
            })

        context['deps'] = deps
        context['confirmation'] = True
        return context

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        if unicode(self.object) != request.POST.get('confirm'):
            messages.error(request, _(u"Object name does not match!"))
            return self.get(request, *args, **kwargs)

        response = super(HostDelete, self).delete(request, *args, **kwargs)
        messages.success(request, _(u"Host successfully deleted!"))
        return response


class RecordList(LoginRequiredMixin, SuperuserRequiredMixin, SingleTableView):
    model = Record
    table_class = RecordTable
    template_name = "network/record-list.html"
    table_pagination = False

    def get_context_data(self, **kwargs):
        context = super(RecordList, self).get_context_data(**kwargs)
        context['types'] = Record.CHOICES_type
        return context

    def get_table_data(self):
        type_id = self.request.GET.get('type')
        if type_id:
            data = Record.objects.filter(type=type_id).select_related()
        else:
            data = Record.objects.select_related()
        return data


class RecordDetail(LoginRequiredMixin, SuperuserRequiredMixin,
                   SuccessMessageMixin, UpdateView):
    model = Record
    template_name = "network/record-edit.html"
    form_class = RecordForm
    # TODO fqdn
    success_message = _(u'Successfully modified record!')

    def get_context_data(self, **kwargs):
        context = super(RecordDetail, self).get_context_data(**kwargs)
        context['fqdn'] = self.object.fqdn
        context['record_pk'] = self.object.pk
        return context

    def get_success_url(self):
        if 'pk' in self.kwargs:
            return reverse_lazy('network.record', kwargs=self.kwargs)


class RecordCreate(LoginRequiredMixin, SuperuserRequiredMixin,
                   SuccessMessageMixin, CreateView):
    model = Record
    template_name = "network/record-create.html"
    form_class = RecordForm
    # TODO fqdn
    success_message = _(u'Successfully created record!')

    def get_initial(self):
        return {
            # 'owner': 1,
            'domain': self.request.GET.get('domain'),
        }


class RecordDelete(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = Record
    template_name = "network/confirm/base_delete.html"

    def get_success_url(self):
        next = self.request.POST.get('next')
        if next:
            return self.request.POST['next']
        else:
            return reverse_lazy('network.record_list')


class RuleList(LoginRequiredMixin, SuperuserRequiredMixin, SingleTableView):
    model = Rule
    table_class = RuleTable
    template_name = "network/rule-list.html"
    table_pagination = False

    def get_table_data(self):
        return Rule.objects.select_related('host', 'hostgroup', 'vlan',
                                           'vlangroup', 'firewall',
                                           'foreign_network', 'owner')


class RuleDetail(LoginRequiredMixin, SuperuserRequiredMixin,
                 SuccessMessageMixin, UpdateView):
    model = Rule
    template_name = "network/rule-edit.html"
    form_class = RuleForm
    success_message = _(u'Successfully modified rule!')

    def get_success_url(self):
        if 'pk' in self.kwargs:
            return reverse_lazy('network.rule', kwargs=self.kwargs)

    def get_context_data(self, **kwargs):
        context = super(RuleDetail, self).get_context_data(**kwargs)

        rule = self.get_object()

        context['rule'] = rule
        return context


class RuleCreate(LoginRequiredMixin, SuperuserRequiredMixin,
                 SuccessMessageMixin, CreateView):
    model = Rule
    template_name = "network/rule-create.html"
    form_class = RuleForm
    success_message = _(u'Successfully created rule!')

    def get_initial(self):
        return {
            # 'owner': 1,
            'host': self.request.GET.get('host'),
            'hostgroup': self.request.GET.get('hostgroup')
        }


class RuleDelete(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = Rule
    template_name = "network/confirm/base_delete.html"

    def get_success_url(self):
        next = self.request.POST.get('next')
        if next:
            return next
        else:
            return reverse_lazy('network.rule_list')


class SwitchPortList(LoginRequiredMixin, SuperuserRequiredMixin,
                     SingleTableView):
    model = SwitchPort
    table_class = SwitchPortTable
    template_name = "network/switch-port-list.html"
    table_pagination = False


class SwitchPortDetail(LoginRequiredMixin, SuperuserRequiredMixin,
                       SuccessMessageMixin, UpdateView):
    model = SwitchPort
    template_name = "network/switch-port-edit.html"
    form_class = SwitchPortForm
    success_message = _(u'Succesfully modified switch port!')

    def get_success_url(self):
        if 'pk' in self.kwargs:
            return reverse_lazy('network.switch_port', kwargs=self.kwargs)

    def get_context_data(self, **kwargs):
        context = super(SwitchPortDetail, self).get_context_data(**kwargs)
        context['switch_port_pk'] = self.object.pk
        context['devices'] = EthernetDevice.objects.filter(
            switch_port=self.object.pk)
        return context


class SwitchPortCreate(LoginRequiredMixin, SuperuserRequiredMixin,
                       SuccessMessageMixin, CreateView):
    model = SwitchPort
    template_name = "network/switch-port-create.html"
    form_class = SwitchPortForm
    success_message = _(u'Successfully created switch port!')


class SwitchPortDelete(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = SwitchPort
    template_name = "network/confirm/base_delete.html"

    def get_success_url(self):
        next = self.request.POST.get('next')
        if next:
            return next
        else:
            return reverse_lazy('network.switch_port_list')


class VlanList(LoginRequiredMixin, SuperuserRequiredMixin, SingleTableView):
    model = Vlan
    table_class = VlanTable
    template_name = "network/vlan-list.html"
    table_pagination = False


class VlanAclUpdateView(AclUpdateView):
    model = Vlan


class VlanDetail(LoginRequiredMixin, SuperuserRequiredMixin,
                 SuccessMessageMixin, UpdateView):
    model = Vlan
    template_name = "network/vlan-edit.html"
    form_class = VlanForm
    slug_field = 'vid'
    slug_url_kwarg = 'vid'
    success_message = _(u'Succesfully modified vlan %(name)s!')

    def get_context_data(self, **kwargs):
        context = super(VlanDetail, self).get_context_data(**kwargs)

        q = Host.objects.filter(interface__in=Interface.objects.filter(
            vlan=self.object, instance__destroyed_at=None
        ))

        context['host_list'] = SmallHostTable(q)
        context['vlan_vid'] = self.kwargs.get('vid')
        context['acl'] = AclUpdateView.get_acl_data(
            self.object, self.request.user, 'network.vlan-acl')
        context['aclform'] = AclUserAddForm()
        return context

    success_url = reverse_lazy('network.vlan_list')


class VlanCreate(LoginRequiredMixin, SuperuserRequiredMixin,
                 SuccessMessageMixin, CreateView):
    model = Vlan
    template_name = "network/vlan-create.html"
    form_class = VlanForm
    success_message = _(u'Successfully created vlan %(name)s!')


class VlanDelete(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = Vlan
    template_name = "network/confirm/base_delete.html"

    def get_success_url(self):
        next = self.request.POST.get('next')
        if next:
            return next
        else:
            return reverse_lazy('network.vlan_list')

    def get_object(self, queryset=None):
        """ we identify vlans by vid and not pk """
        return Vlan.objects.get(vid=self.kwargs['vid'])

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        if unicode(self.object) != request.POST.get('confirm'):
            messages.error(request, _(u"Object name does not match!"))
            return self.get(request, *args, **kwargs)

        response = super(VlanDelete, self).delete(request, *args, **kwargs)
        messages.success(request, _(u"Vlan successfully deleted!"))
        return response

    def get_context_data(self, **kwargs):
        context = super(VlanDelete, self).get_context_data(**kwargs)

        deps = []
        # hosts
        hosts = Host.objects.filter(vlan=self.object).all()
        if len(hosts) > 0:
            deps.append({
                'name': _('Hosts'),
                'data': hosts
            })

            # records
            records = Record.objects.filter(host__in=deps[0]['data'])
            if len(records) > 0:
                deps.append({
                    'name': _('Records'),
                    'data':  records
                })

        context['deps'] = deps
        context['confirmation'] = True
        return context


class VlanGroupList(LoginRequiredMixin, SuperuserRequiredMixin,
                    SingleTableView):
    model = VlanGroup
    table_class = VlanGroupTable
    template_name = "network/vlan-group-list.html"
    table_pagination = False


class VlanGroupDetail(LoginRequiredMixin, SuperuserRequiredMixin,
                      SuccessMessageMixin, UpdateView):
    model = VlanGroup
    template_name = "network/vlan-group-edit.html"
    form_class = VlanGroupForm
    success_url = reverse_lazy('network.vlan_group_list')
    success_message = _(u'Successfully modified vlan group %(name)s!')

    def get_context_data(self, *args, **kwargs):
        context = super(VlanGroupDetail, self).get_context_data(**kwargs)
        context['vlangroup_pk'] = self.object.pk
        return context


class VlanGroupCreate(LoginRequiredMixin, SuperuserRequiredMixin,
                      SuccessMessageMixin, CreateView):
    model = VlanGroup
    template_name = "network/vlan-group-create.html"
    form_class = VlanGroupForm
    success_message = _(u'Successfully created vlan group %(name)s!')


class VlanGroupDelete(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = VlanGroup
    template_name = "network/confirm/base_delete.html"

    def get_success_url(self):
        next = self.request.POST.get('next')
        if next:
            return next
        else:
            return reverse_lazy('network.vlan_group_list')


def remove_host_group(request, **kwargs):
    host = Host.objects.get(pk=kwargs['pk'])
    group = Group.objects.get(pk=kwargs['group_pk'])

    # for get we show the confirmation page
    if request.method == "GET":
        return render(request,
                      'network/confirm/remove_host_group.html',
                      {
                          'group': group.name,
                          'host': host.hostname
                      })

    # for post we actually remove the group from the host
    elif request.method == "POST":
        host.groups.remove(group)
        if not request.is_ajax():
            messages.success(request, _(u"Successfully removed %(host)s from "
                                        "%(group)s group!" % {
                                            'host': host,
                                            'group': group
                                        }))
        return redirect(reverse_lazy('network.host',
                                     kwargs={'pk': kwargs['pk']}))


def add_host_group(request, **kwargs):
    group_pk = request.POST.get('group')
    if request.method == "POST" and group_pk:
        host = Host.objects.get(pk=kwargs['pk'])
        group = Group.objects.get(pk=group_pk)
        host.groups.add(group)
        if not request.is_ajax():
            messages.success(request, _(u"Successfully added %(host)s to group"
                                        " %(group)s!" % {
                                            'host': host,
                                            'group': group
                                        }))
        return redirect(reverse_lazy('network.host', kwargs=kwargs))


def remove_switch_port_device(request, **kwargs):
    device = EthernetDevice.objects.get(pk=kwargs['device_pk'])
    # for get we show the confirmation page
    if request.method == "GET":
        return render(request, 'network/confirm/base_delete.html',
                      {'object': device})

    # for post we actually remove the group from the host
    elif request.method == "POST":
        device.delete()
        if not request.is_ajax():
            messages.success(request, _(u"Successfully deleted ethernet device"
                                        " %(name)s!" % {
                                            'name': device.name,
                                        }))
        return redirect(reverse_lazy('network.switch_port',
                                     kwargs={'pk': kwargs['pk']}))


def add_switch_port_device(request, **kwargs):
    device_name = request.POST.get('device_name')

    if (request.method == "POST" and device_name and len(device_name) > 0
       and EthernetDevice.objects.filter(name=device_name).count() == 0):

        switch_port = SwitchPort.objects.get(pk=kwargs['pk'])
        new_device = EthernetDevice(name=device_name, switch_port=switch_port)
        new_device.save()
        if not request.is_ajax():
            messages.success(request, _(u"Successfully added %(name)s to this"
                                        " switch port" % {
                                            'name': device_name,
                                        }))
        return redirect(reverse_lazy('network.switch_port', kwargs=kwargs))

    elif not len(device_name) > 0:
        messages.error(request, _("Ethernet device name cannot be empty!"))
        return redirect(reverse_lazy('network.switch_port', kwargs=kwargs))
    elif EthernetDevice.objects.get(name=device_name) is not None:
        messages.error(request, _("There is already an ethernet device with"
                                  " that name!"))
        return redirect(reverse_lazy('network.switch_port', kwargs=kwargs))
