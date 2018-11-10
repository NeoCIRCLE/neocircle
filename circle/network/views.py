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

import logging
import random
import json
from collections import OrderedDict

from netaddr import IPNetwork
from django.views.generic import (
    TemplateView, UpdateView, DeleteView, CreateView,
)
from django.core.exceptions import (
    ValidationError, PermissionDenied, ImproperlyConfigured
)
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, Http404
from django.db.models import Q
from django.conf import settings

from django_tables2 import SingleTableView

from firewall.models import (
    Host, Vlan, Domain, Group, Record, BlacklistItem, Rule, VlanGroup,
    SwitchPort, EthernetDevice, Firewall
)
from network.models import Vxlan, EditorElement
from vm.models import Interface, Instance
from common.views import CreateLimitedResourceMixin
from acl.views import CheckedObjectMixin
from .tables import (
    HostTable, VlanTable, SmallHostTable, DomainTable, GroupTable,
    RecordTable, BlacklistItemTable, RuleTable, VlanGroupTable,
    SmallRuleTable, SmallGroupRuleTable, SmallRecordTable, SwitchPortTable,
    SmallDhcpTable, FirewallTable, FirewallRuleTable, VxlanTable, SmallVmTable,
)
from .forms import (
    HostForm, VlanForm, DomainForm, GroupForm, RecordForm, BlacklistItemForm,
    RuleForm, VlanGroupForm, SwitchPortForm, FirewallForm,
    VxlanForm, VxlanSuperUserForm,
)

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic.edit import FormMixin
from django.utils.translation import ugettext_lazy as _
from braces.views import LoginRequiredMixin, SuperuserRequiredMixin
from operator import itemgetter
from itertools import chain
from dashboard.views import AclUpdateView
from dashboard.forms import AclUserOrGroupAddForm

try:
    from django.http import JsonResponse
except ImportError:
    from django.utils import simplejson

    class JsonResponse(HttpResponse):
        """JSON response for Django < 1.7
        https://gist.github.com/philippeowagner/3179eb475fe1795d6515
        """
        def __init__(self, content, mimetype='application/json',
                     status=None, content_type=None):
            super(JsonResponse, self).__init__(
                content=simplejson.dumps(content),
                mimetype=mimetype,
                status=status,
                content_type=content_type)


logger = logging.getLogger(__name__)


class MagicMixin(object):

    def get(self, *args, **kwargs):
        if self.request.is_ajax():
            result = self._get_ajax(*args, **kwargs)
            return JsonResponse({k: unicode(result[k] or "") for k in result})
        else:
            return super(MagicMixin, self).get(*args, **kwargs)


class InitialOwnerMixin(FormMixin):
    def get_initial(self):
        initial = super(InitialOwnerMixin, self).get_initial()
        initial['owner'] = self.request.user
        return initial


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
    success_message = _(u'Successfully modified blacklist item %(ipv4)s.')

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
    success_message = _(u'Successfully created blacklist item %(ipv4)s')


class BlacklistDelete(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = BlacklistItem
    template_name = "network/confirm/base_delete.html"

    def get_context_data(self, **kwargs):
        """ display more information about the object """
        context = super(BlacklistDelete, self).get_context_data(**kwargs)
        if 'pk' in self.kwargs:
            to_delete = BlacklistItem.objects.get(pk=self.kwargs['pk'])
            context['object'] = "%s - %s" % (to_delete.ipv4, to_delete.reason)
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
    success_message = _(u'Successfully modified domain %(name)s.')

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
                   SuccessMessageMixin, InitialOwnerMixin, CreateView):
    model = Domain
    template_name = "network/domain-create.html"
    form_class = DomainForm
    success_message = _(u'Successfully created domain %(name)s.')


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
            messages.error(request, _(u"Object name does not match."))
            return self.get(request, *args, **kwargs)

        response = super(DomainDelete, self).delete(request, *args, **kwargs)
        messages.success(request, _(u"Domain successfully deleted."))
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


class FirewallList(LoginRequiredMixin, SuperuserRequiredMixin,
                   SingleTableView):
    model = Firewall
    table_class = FirewallTable
    template_name = "network/firewall-list.html"
    table_pagination = False


class FirewallDetail(LoginRequiredMixin, SuperuserRequiredMixin,
                     SuccessMessageMixin, UpdateView):
    model = Firewall
    template_name = "network/firewall-edit.html"
    form_class = FirewallForm
    success_message = _(u'Succesfully modified firewall.')

    def get_success_url(self):
        if 'pk' in self.kwargs:
            return reverse_lazy('network.firewall', kwargs=self.kwargs)

    def get_context_data(self, **kwargs):
        context = super(FirewallDetail, self).get_context_data(**kwargs)
        rules = Rule.objects.filter(firewall=self.object)
        context['rule_table'] = FirewallRuleTable(rules,
                                                  request=self.request)
        return context


class FirewallCreate(LoginRequiredMixin, SuperuserRequiredMixin,
                     SuccessMessageMixin, CreateView):
    model = Firewall
    template_name = "network/firewall-create.html"
    form_class = FirewallForm
    success_message = _(u'Successfully created firewall.')


class FirewallDelete(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = Firewall
    template_name = "network/confirm/base_delete.html"

    def get_success_url(self):
        next = self.request.POST.get('next')
        if next:
            return next
        else:
            return reverse_lazy('network.firewall_list')


class GroupList(LoginRequiredMixin, SuperuserRequiredMixin, SingleTableView):
    model = Group
    table_class = GroupTable
    template_name = "network/group-list.html"
    table_pagination = False


class GroupCreate(LoginRequiredMixin, SuperuserRequiredMixin,
                  SuccessMessageMixin, InitialOwnerMixin, CreateView):
    model = Group
    template_name = "network/group-create.html"
    form_class = GroupForm
    success_message = _(u'Successfully created host group %(name)s.')


class GroupDetail(LoginRequiredMixin, SuperuserRequiredMixin,
                  SuccessMessageMixin, UpdateView):
    model = Group
    template_name = "network/group-edit.html"
    form_class = GroupForm
    success_message = _(u'Successfully modified host group %(name)s.')

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


class HostMagicMixin(MagicMixin):
    def _get_ajax(self, *args, **kwargs):
        GET = self.request.GET
        result = {}
        vlan = get_object_or_404(Vlan.objects, pk=GET.get("vlan", ""))
        if "ipv4" in GET:
            try:
                result["ipv6"] = vlan.convert_ipv4_to_ipv6(GET["ipv4"]) or ""
            except:
                result["ipv6"] = ""
        else:
            try:
                result.update(vlan.get_new_address())
            except ValidationError:
                result["ipv4"] = ""
                result["ipv6"] = ""
        return result


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

        search = self.request.GET.get("s")
        if search:
            data = data.filter(Q(hostname__icontains=search) |
                               Q(ipv4=search))  # ipv4 does not work TODO
        return data


class HostDetail(HostMagicMixin, LoginRequiredMixin, SuperuserRequiredMixin,
                 SuccessMessageMixin, UpdateView):
    model = Host
    template_name = "network/host-edit.html"
    form_class = HostForm
    success_message = _(u'Successfully modified host %(hostname)s.')

    def _get_ajax(self, *args, **kwargs):
        if "vlan" not in self.request.GET:
            host = Host.objects.get(pk=kwargs['pk'])
            host = {
                'hostname': host.hostname,
                'ipv4': str(host.ipv4),
                'ipv6': str(host.ipv6),
                'fqdn': host.get_fqdn()
            }
            return host
        else:
            return super(HostDetail, self)._get_ajax(*args, **kwargs)

    def get(self, request, *args, **kwargs):
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


class HostCreate(HostMagicMixin, LoginRequiredMixin, SuperuserRequiredMixin,
                 SuccessMessageMixin, CreateView):
    model = Host
    template_name = "network/host-create.html"
    form_class = HostForm
    success_message = _(u'Successfully created host %(hostname)s.')

    def get_initial(self):
        initial = super(HostCreate, self).get_initial()

        for i in ("vlan", "mac", "hostname"):
            if i in self.request.GET and i not in self.request.POST:
                initial[i] = self.request.GET[i]
        if "vlan" in initial:
            if not initial['vlan'].isnumeric():
                raise Http404()
            vlan = get_object_or_404(Vlan.objects, pk=initial['vlan'])
            try:
                initial.update(vlan.get_new_address())
            except ValidationError as e:
                messages.error(self.request, e.message)
        return initial


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
            messages.error(request, _(u"Object name does not match."))
            return self.get(request, *args, **kwargs)

        response = super(HostDelete, self).delete(request, *args, **kwargs)
        messages.success(request, _(u"Host successfully deleted."))
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
    success_message = _(u'Successfully modified record.')

    def get_context_data(self, **kwargs):
        context = super(RecordDetail, self).get_context_data(**kwargs)
        context['fqdn'] = self.object.fqdn
        context['record_pk'] = self.object.pk
        return context

    def get_success_url(self):
        if 'pk' in self.kwargs:
            return reverse_lazy('network.record', kwargs=self.kwargs)


class RecordCreate(LoginRequiredMixin, SuperuserRequiredMixin,
                   SuccessMessageMixin, InitialOwnerMixin, CreateView):
    model = Record
    template_name = "network/record-create.html"
    form_class = RecordForm
    # TODO fqdn
    success_message = _(u'Successfully created record.')

    def get_initial(self):
        initial = super(RecordCreate, self).get_initial()
        initial['domain'] = self.request.GET.get('domain')

        host_pk = self.request.GET.get("host")
        try:
            host = Host.objects.get(pk=host_pk)
        except (Host.DoesNotExist, ValueError):
            host = None

        if host:
            initial.update({
                'type': "CNAME",
                'host': host,
                'address': host.get_fqdn(),
            })

        return initial


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

    def get_context_data(self, **kwargs):
        self.types = OrderedDict([
            ('vlan', _("Vlan")), ('vlangroup', _("Vlan group")),
            ('host', _("Host")), ('hostgroup', _("Host group")),
            ('firewall', _("Firewall"))
        ])
        context = super(RuleList, self).get_context_data(**kwargs)
        context['types'] = self.types
        return context

    def get_table_data(self):
        rules = Rule.objects.select_related('host', 'hostgroup', 'vlan',
                                            'vlangroup', 'firewall',
                                            'foreign_network', 'owner')

        rule_type = self.request.GET.get("type")
        if rule_type and rule_type in self.types.keys():
            rules = rules.filter(**{'%s__isnull' % rule_type: False})
        return rules


class RuleDetail(LoginRequiredMixin, SuperuserRequiredMixin,
                 SuccessMessageMixin, UpdateView):
    model = Rule
    template_name = "network/rule-edit.html"
    form_class = RuleForm
    success_message = _(u'Successfully modified rule.')

    def get_success_url(self):
        if 'pk' in self.kwargs:
            return reverse_lazy('network.rule', kwargs=self.kwargs)

    def get_context_data(self, **kwargs):
        context = super(RuleDetail, self).get_context_data(**kwargs)

        rule = self.get_object()

        context['rule'] = rule
        return context


class RuleCreate(LoginRequiredMixin, SuperuserRequiredMixin,
                 SuccessMessageMixin, InitialOwnerMixin, CreateView):
    model = Rule
    template_name = "network/rule-create.html"
    form_class = RuleForm
    success_message = _(u'Successfully created rule.')

    def get_initial(self):
        initial = super(RuleCreate, self).get_initial()
        initial.update({
            'host': self.request.GET.get('host'),
            'hostgroup': self.request.GET.get('hostgroup')
        })
        return initial


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
    success_message = _(u'Succesfully modified switch port.')

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
    success_message = _(u'Successfully created switch port.')


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


class VlanMagicMixin(MagicMixin):
    def _get_ajax(self, *args, **kwargs):
        GET = self.request.GET
        result = {}
        if "network4" in GET and "network6" in GET:
            try:
                result["ipv6_template"], result["host_ipv6_prefixlen"] = (
                    Vlan._magic_ipv6_template(IPNetwork(GET['network4']),
                                              IPNetwork(GET['network6'])))
            except:
                result["ipv6_template"] = result["host_ipv6_prefixlen"] = ""
        return result


class VlanDetail(VlanMagicMixin, LoginRequiredMixin, SuperuserRequiredMixin,
                 SuccessMessageMixin, UpdateView):
    model = Vlan
    template_name = "network/vlan-edit.html"
    form_class = VlanForm
    slug_field = 'vid'
    slug_url_kwarg = 'vid'
    success_message = _(u'Succesfully modified vlan %(name)s.')
    success_url = reverse_lazy('network.vlan_list')

    def get_context_data(self, **kwargs):
        context = super(VlanDetail, self).get_context_data(**kwargs)
        context['host_list'] = SmallHostTable(self.object.host_set.all())
        context['dhcp_list'] = SmallDhcpTable(self.object.get_dhcp_clients())
        context['vlan_vid'] = self.kwargs.get('vid')
        context['acl'] = AclUpdateView.get_acl_data(
            self.object, self.request.user, 'network.vlan-acl')
        context['aclform'] = AclUserOrGroupAddForm()
        return context


class VlanCreate(VlanMagicMixin, LoginRequiredMixin, SuperuserRequiredMixin,
                 SuccessMessageMixin, InitialOwnerMixin, CreateView):
    model = Vlan
    template_name = "network/vlan-create.html"
    form_class = VlanForm
    success_message = _(u'Successfully created vlan %(name)s.')


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
            messages.error(request, _(u"Object name does not match."))
            return self.get(request, *args, **kwargs)

        response = super(VlanDelete, self).delete(request, *args, **kwargs)
        messages.success(request, _(u"Vlan successfully deleted."))
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
    success_message = _(u'Successfully modified vlan group %(name)s.')

    def get_context_data(self, *args, **kwargs):
        context = super(VlanGroupDetail, self).get_context_data(**kwargs)
        context['vlangroup_pk'] = self.object.pk
        return context


class VlanGroupCreate(LoginRequiredMixin, SuperuserRequiredMixin,
                      SuccessMessageMixin, InitialOwnerMixin, CreateView):
    model = VlanGroup
    template_name = "network/vlan-group-create.html"
    form_class = VlanGroupForm
    success_message = _(u'Successfully created vlan group %(name)s.')


class VlanGroupDelete(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = VlanGroup
    template_name = "network/confirm/base_delete.html"

    def get_success_url(self):
        next = self.request.POST.get('next')
        if next:
            return next
        else:
            return reverse_lazy('network.vlan_group_list')


class VxlanList(LoginRequiredMixin, SingleTableView):
    model = Vxlan
    table_class = VxlanTable
    table_pagination = False

    def get_template_names(self):
        if self.request.user.is_superuser:
            return ["network/vxlan-superuser-list.html"]
        else:
            return ["network/vxlan-list.html"]

    def get_queryset(self):
        return Vxlan.get_objects_with_level('user', self.request.user)

    def get(self, *args, **kwargs):
        if self.request.is_ajax():
            return self._create_ajax_request()
        return super(VxlanList, self).get(*args, **kwargs)

    def _create_ajax_request(self):
        vxlans = self.get_queryset()
        vxlans = [{
            'pk': i.pk,
            'url': reverse_lazy('network.vxlan', args=[i.pk]),
            'icon': 'fa-sitemap',
            'name': i.name,
            'vni': i.vni if self.request.user.is_superuser else None
        } for i in vxlans]
        return JsonResponse(list(vxlans), safe=False)


class VxlanAclUpdateView(AclUpdateView):
    model = Vxlan


class VxlanDetail(LoginRequiredMixin, CheckedObjectMixin,
                  SuccessMessageMixin, UpdateView):
    model = Vxlan
    slug_field = 'vni'
    slug_url_kwarg = 'vni'
    success_message = _(u'Succesfully modified vlan %(name)s.')
    success_url = reverse_lazy('network.vxlan-list')

    def get_template_names(self):
        if self.request.user.is_superuser:
            return ["network/vxlan-superuser-edit.html"]
        else:
            return ["network/vxlan-edit.html"]

    def get_form_class(self, is_post=False):
        if self.request.user.is_superuser:
            return VxlanSuperUserForm
        return VxlanForm

    def get_context_data(self, **kwargs):
        context = super(VxlanDetail, self).get_context_data(**kwargs)
        context['vm_list'] = SmallVmTable(self.object.vm_interface.all())
        context['acl'] = AclUpdateView.get_acl_data(
            self.object, self.request.user, 'network.vxlan-acl')
        context['aclform'] = AclUserOrGroupAddForm()
        return context

    def post(self, *args, **kwargs):
        if not self.object.has_level(self.request.user, 'owner'):
            raise PermissionDenied()
        return super(VxlanDetail, self).post(*args, **kwargs)


class VxlanCreate(LoginRequiredMixin, CreateLimitedResourceMixin,
                  SuccessMessageMixin, InitialOwnerMixin, CreateView):
    model = Vxlan
    profile_attribute = 'network_limit'
    resource_name = _('Virtual network')
    success_message = _(u'Successfully created vxlan %(name)s.')

    def get_template_names(self):
        if self.request.user.is_superuser:
            return ["network/vxlan-superuser-create.html"]
        else:
            return ["network/vxlan-create.html"]

    def get_form_class(self, is_post=False):
        if self.request.user.is_superuser:
            return VxlanSuperUserForm
        return VxlanForm

    def get_initial(self):
        initial = super(VxlanCreate, self).get_initial()
        initial['vni'] = self._generate_vni()
        return initial

    def get_default_vlan(self):
        vlan = Vlan.objects.filter(
            name=settings.DEFAULT_USERNET_VLAN_NAME).first()
        if vlan is None:
            msg = (_('Cannot find server vlan: %s') %
                   settings.DEFAULT_USERNET_VLAN_NAME)
            if self.request.user.is_superuser:
                messages.error(self.request, msg)
            logger.error(msg)
            raise ImproperlyConfigured()
        return vlan

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.owner = self.request.user
        obj.vlan = self.get_default_vlan()
        try:
            obj.full_clean()
            obj.save()
            obj.set_level(obj.owner, 'owner')
            self.object = obj
        except Exception as e:
            msg = _('Unexpected error occured. '
                    'Please try again or contact administrator!')
            messages.error(self.request, msg)
            logger.exception(e)
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        # When multiple client get same VNI value
        if 'vni' in form.errors.as_data():
            messages.error(self.request, _('Cannot create virtual network.'
                                           ' Please try again.'))
            return redirect('network.vxlan-create')
        return super(VxlanCreate, self).form_invalid(form)

    def _generate_vni(self):
        if Vxlan.objects.count() == settings.USERNET_MAX:
            msg = _('Cannot find unused VNI value. '
                    'Please contact administrator!')
            messages.error(self.request, msg)
            logger.error(msg)
        else:
            full_range = set(range(0, settings.USERNET_MAX))
            used_values = {vni[0] for vni in Vxlan.objects.values_list('vni')}
            free_values = full_range - used_values
            return random.choice(list(free_values))


class VxlanDelete(LoginRequiredMixin, CheckedObjectMixin, DeleteView):
    model = Vlan
    read_level = 'owner'

    def get_template_names(self):
        if self.request.user.is_superuser:
            return ["network/confirm/base_delete.html"]
        else:
            return ["dashboard/confirm/base-delete.html"]

    def get_success_url(self):
        next = self.request.POST.get('next')
        if next:
            return next
        else:
            return reverse_lazy('network.vxlan-list')

    def get_object(self, queryset=None):
        """ we identify vlans by vid and not pk """
        return Vxlan.objects.get(vni=self.kwargs['vni'])

    def delete(self, request, *args, **kwargs):
        if self.request.user.is_superuser:
            self.object = self.get_object()
            if unicode(self.object) != request.POST.get('confirm'):
                messages.error(request, _(u"Object name does not match."))
                return self.get(request, *args, **kwargs)

        response = super(VxlanDelete, self).delete(request, *args, **kwargs)
        messages.success(request, _(u"Vxlan successfully deleted."))
        return response

    def get_context_data(self, **kwargs):
        context = super(VxlanDelete, self).get_context_data(**kwargs)
        if self.request.user.is_superuser:
            context['confirmation'] = True
        return context


class NetworkEditorView(LoginRequiredMixin, TemplateView):
    template_name = 'network/editor.html'

    def get(self, *args, **kwargs):
        if self.request.is_ajax():
            connections = self._get_connections()

            ngelements = self._get_nongraph_elements(connections)
            ngelements = self._serialize_elements(ngelements)

            connections = map(lambda con: {
               'source': 'vm-%s' % con['source'].pk,
               'target': 'net-%s' % con['target'].vni,
            }, connections['connections'])

            unused_elements = self._get_unused_elements()
            unused_elements = self._serialize_elements(unused_elements)

            return JsonResponse({
                'elements': map(lambda e: e.as_data(),
                                EditorElement.objects.filter(
                                    owner=self.request.user)),
                'nongraph_elements': ngelements,
                'unused_elements': unused_elements,
                'connections': connections,
            })
        return super(NetworkEditorView, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body)
        add_ifs = data.get('add_interfaces', [])
        remove_ifs = data.get('remove_interfaces', [])
        add_nodes = data.get('add_nodes', [])
        remove_nodes = data.get('remove_nodes', [])

        # Add editor element
        self._element_list_operation(add_nodes, self._update_element)
        # Remove editor element
        self._element_list_operation(remove_nodes, self._remove_element)

        # Add interface
        self._interface_list_operation(add_ifs, self._add_interface)
        # Remove interface
        self._interface_list_operation(remove_ifs, self._remove_interface)

        return self.get(*args, **kwargs)

    def _max_port_num_helper(self, model, attr_name):
        if not hasattr(self, attr_name):
            value = model.get_objects_with_level(
                'user', self.request.user).count()
            setattr(self, attr_name, value)
        return getattr(self, attr_name)

    @property
    def vm_max_port_num(self):
        return self._max_port_num_helper(Vxlan, '_vm_max_port_num')

    @property
    def vxlan_max_port_num(self):
        return self._max_port_num_helper(Instance, '_vxlan_max_port_num')

    def _vm_serializer(self, vm):
        max_port_num = self.vm_max_port_num
        vxlans = Vxlan.get_objects_with_level(
            'user', self.request.user).values_list('pk', flat=True)
        free_port_num = max_port_num - vm.interface_set.filter(
            vxlan__pk__in=vxlans).count()
        return {
            'name': unicode(vm),
            'id': 'vm-%s' % vm.pk,
            'description': vm.description,
            'type': 'vm',
            'icon': 'fa-desktop',
            'free_port_num': free_port_num,
        }

    def _vxlan_serializer(self, vxlan):
        max_port_num = self.vxlan_max_port_num
        vms = Instance.get_objects_with_level(
            'user', self.request.user).values_list('pk', flat=True)
        free_port_num = max_port_num - Interface.objects.filter(
            vxlan=vxlan, instance__pk__in=vms).count()
        return {
            'name': vxlan.name,
            'id': 'net-%s' % vxlan.vni,
            'description': vxlan.description,
            'type': 'network',
            'icon': 'fa-sitemap',
            'free_port_num': free_port_num,
        }

    def _get_unused_elements(self):
        connections = self._get_connections()
        vms = map(lambda vm: vm.id, connections['vms'])
        vxlans = map(lambda vxlan: vxlan.vni, connections['vxlans'])
        eelems = EditorElement.objects.filter(owner=self.request.user)

        vm_query = Q(pk__in=vms) | Q(editor_elements__in=eelems)
        vms = Instance.get_objects_with_level(
            'user', self.request.user).exclude(vm_query)
        vxlan_query = Q(vni__in=vms) | Q(editor_elements__in=eelems)
        vxlans = Vxlan.get_objects_with_level(
            'user', self.request.user).exclude(vxlan_query)
        return {
            'vms': vms,
            'vxlans': vxlans,
        }

    def _get_nongraph_elements(self, connections):
        return {
            'vms': filter(lambda v: not v.editor_elements.exists(),
                          connections['vms']),
            'vxlans': filter(lambda v: not v.editor_elements.exists(),
                             connections['vxlans']),
        }

    def _get_connections(self):
        """ Returns connections and theirs participants. """
        vms = Instance.get_objects_with_level('user', self.request.user)
        connections = []
        vm_set = set()
        vxlan_set = set()
        for vm in vms:
            for intf in vm.interface_set.filter(vxlan__isnull=False):
                vm_set.add(vm)
                vxlan_set.add(intf.vxlan)
                connections.append({
                    'source': vm,
                    'target': intf.vxlan,
                })
        return {
            'connections': connections,
            'vms': vm_set,
            'vxlans': vxlan_set,
        }

    def _serialize_elements(self, elements):
        return (map(self._vm_serializer, elements['vms']) +
                map(self._vxlan_serializer, elements['vxlans']))

    def _get_modifiable_object(self, model, connection,
                               attr_name, filter_attr):
        value = connection.get(attr_name)
        if value is not None:
            value = model.get_objects_with_level(
                'user', self.request.user).filter(
                    **{filter_attr: value}).first()
        return value

    def _element_list_operation(self, node_list, operation):
        for e in node_list:
            elem = dict(e)
            type = elem.pop('type')
            id = elem.pop('id')
            model = Instance if type == 'vm' else Vxlan
            filter = {'pk': id} if type == 'vm' else {'vni': id}
            object = model.get_objects_with_level(
                'user', self.request.user).get(**filter)
            operation(object.editor_elements, elem)

    def _update_element(self, elements, elem):
        elements.update_or_create(owner=self.request.user,
                                  defaults=elem)

    def _remove_element(self, elements, elem):
        elements.filter(owner=self.request.user).delete()

    def _interface_list_operation(self, if_list, operation):
        for con in if_list:
            vm = self._get_modifiable_object(Instance, con, 'source', 'pk')
            vxlan = self._get_modifiable_object(Vxlan, con, 'target', 'vni')
            if vm and vxlan:
                operation(vm, vxlan)

    def _add_interface(self, vm, vxlan):
        vm.add_user_interface(
            user=self.request.user, vxlan=vxlan, system=vm.system)

    def _remove_interface(self, vm, vxlan):
        intf = vm.interface_set.filter(vxlan=vxlan).first()
        if intf:
            vm.remove_user_interface(
                interface=intf, user=self.request.user, system=vm.system)


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
                                        "%(group)s group." % {
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
                                        " %(group)s." % {
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
                                        " %(name)s." % {
                                            'name': device.name,
                                        }))
        return redirect(reverse_lazy('network.switch_port',
                                     kwargs={'pk': kwargs['pk']}))


def add_switch_port_device(request, **kwargs):
    device_name = request.POST.get('device_name')

    if (request.method == "POST" and device_name and len(device_name) > 0 and
            EthernetDevice.objects.filter(name=device_name).count() == 0):

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
        messages.error(request, _("Ethernet device name cannot be empty."))
        return redirect(reverse_lazy('network.switch_port', kwargs=kwargs))
    elif EthernetDevice.objects.get(name=device_name) is not None:
        messages.error(request, _("There is already an ethernet device with"
                                  " that name."))
        return redirect(reverse_lazy('network.switch_port', kwargs=kwargs))
