from django.views.generic import (TemplateView, UpdateView, DeleteView,
                                  CreateView)
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import render, redirect
from django.http import HttpResponse

from django_tables2 import SingleTableView

from firewall.models import (Host, Vlan, Domain, Group, Record, Blacklist,
                             Rule, VlanGroup)
from .tables import (HostTable, VlanTable, SmallHostTable, DomainTable,
                     GroupTable, RecordTable, BlacklistTable, RuleTable,
                     VlanGroupTable, SmallRuleTable, SmallGroupRuleTable)
from .forms import (HostForm, VlanForm, DomainForm, GroupForm, RecordForm,
                    BlacklistForm, RuleForm, VlanGroupForm)

from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from itertools import chain
import json


class IndexView(TemplateView):
    template_name = "network/index.html"

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)

        size = 13
        blacklists = Blacklist.objects.all().order_by('-modified_at')[:size]
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


class BlacklistList(SingleTableView):
    model = Blacklist
    table_class = BlacklistTable
    template_name = "network/blacklist-list.html"
    table_pagination = False


class BlacklistDetail(UpdateView):
    model = Blacklist
    template_name = "network/blacklist-edit.html"
    form_class = BlacklistForm

    def get_success_url(self):
        if 'pk' in self.kwargs:
            return reverse_lazy('network.blacklist', kwargs=self.kwargs)

    def get_context_data(self, **kwargs):
        context = super(BlacklistDetail, self).get_context_data(**kwargs)
        context['blacklist_pk'] = self.object.pk
        return context


class BlacklistCreate(CreateView):
    model = Blacklist
    template_name = "network/blacklist-create.html"
    form_class = BlacklistForm


class BlacklistDelete(DeleteView):
    model = Blacklist
    template_name = "network/confirm/base_delete.html"

    def get_context_data(self, **kwargs):
        """ display more information about the object """
        context = super(BlacklistDelete, self).get_context_data(**kwargs)
        if 'pk' in self.kwargs:
            to_delete = Blacklist.objects.get(pk=self.kwargs['pk'])
            context['to_delete'] = "%s - %s - %s" % (to_delete.ipv4,
                                                     to_delete.reason,
                                                     to_delete.type)
            return context

    def get_success_url(self):
        next = self.request.POST.get('next')
        if next:
            return self.request.POST['next']
        else:
            return reverse_lazy('network.blacklist_list')


class DomainList(SingleTableView):
    model = Domain
    table_class = DomainTable
    template_name = "network/domain-list.html"
    table_pagination = False


class DomainDetail(UpdateView):
    model = Domain
    template_name = "network/domain-edit.html"
    form_class = DomainForm

    def get_success_url(self):
        if 'pk' in self.kwargs:
            return reverse_lazy('network.domain', kwargs=self.kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(DomainDetail, self).get_context_data(**kwargs)
        context['domain_pk'] = self.get_object().pk
        return context


class DomainCreate(CreateView):
    model = Domain
    template_name = "network/domain-create.html"
    form_class = DomainForm


class DomainDelete(DeleteView):
    model = Domain
    template_name = "network/confirm/base_delete.html"

    def get_success_url(self):
        next = self.request.POST.get('next')
        if next:
            return self.request.POST['next']
        else:
            return reverse_lazy('network.domain_list')


class GroupList(SingleTableView):
    model = Group
    table_class = GroupTable
    template_name = "network/group-list.html"
    table_pagination = False


class GroupCreate(CreateView):
    model = Group
    template_name = "network/group-create.html"
    form_class = GroupForm


class GroupDetail(UpdateView):
    model = Group
    template_name = "network/group-edit.html"
    form_class = GroupForm

    def get_success_url(self):
        if 'pk' in self.kwargs:
            return reverse_lazy('network.group', kwargs=self.kwargs)


class GroupDelete(DeleteView):
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


class HostList(SingleTableView):
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
            data = Host.objects.filter(vlan=vlan_id).all()
        else:
            data = Host.objects.all()

        return data


class HostDetail(UpdateView):
    model = Host
    template_name = "network/host-edit.html"
    form_class = HostForm

    def get(self, request, *args, **kwargs):
        if request.is_ajax():
            host = Host.objects.get(pk=kwargs['pk'])
            host = {
                'hostname': host.hostname,
                'ipv4': host.ipv4,
                'ipv6': host.ipv6,
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

        return context

    def get_success_url(self):
        if 'pk' in self.kwargs:
            return reverse_lazy('network.host', kwargs=self.kwargs)


class HostCreate(CreateView):
    model = Host
    template_name = "network/host-create.html"
    form_class = HostForm


class HostDelete(DeleteView):
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
                'name': 'Records',
                'data': records
            })

        context['deps'] = deps
        context['confirmation'] = True
        return context

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        if unicode(self.object) != request.POST.get('confirm'):
            messages.error(request, _("Object name does not match!"))
            return self.get(request, *args, **kwargs)

        response = super(HostDelete, self).delete(request, *args, **kwargs)
        messages.success(request, _("Host successfully deleted!"))
        return response


class RecordList(SingleTableView):
    model = Record
    table_class = RecordTable
    template_name = "network/record-list.html"
    table_pagination = False


class RecordDetail(UpdateView):
    model = Record
    template_name = "network/record-edit.html"
    form_class = RecordForm

    def get_context_data(self, **kwargs):
        context = super(RecordDetail, self).get_context_data(**kwargs)
        context['fqdn'] = self.object.fqdn
        context['record_pk'] = self.object.pk
        return context

    def get_success_url(self):
        if 'pk' in self.kwargs:
            return reverse_lazy('network.record', kwargs=self.kwargs)


class RecordCreate(CreateView):
    model = Record
    template_name = "network/record-create.html"
    form_class = RecordForm


class RecordDelete(DeleteView):
    model = Record
    template_name = "network/confirm/base_delete.html"

    def get_success_url(self):
        next = self.request.POST.get('next')
        if next:
            return self.request.POST['next']
        else:
            return reverse_lazy('network.record_list')


class RuleList(SingleTableView):
    model = Rule
    table_class = RuleTable
    template_name = "network/rule-list.html"
    table_pagination = False


class RuleDetail(UpdateView):
    model = Rule
    template_name = "network/rule-edit.html"
    form_class = RuleForm

    def get_success_url(self):
        if 'pk' in self.kwargs:
            return reverse_lazy('network.rule', kwargs=self.kwargs)

    def get_context_data(self, **kwargs):
        context = super(RuleDetail, self).get_context_data(**kwargs)

        rule = self.get_object()

        context['rule'] = rule
        return context


class RuleCreate(CreateView):
    model = Rule
    template_name = "network/rule-create.html"
    form_class = RuleForm


class RuleDelete(DeleteView):
    model = Rule
    template_name = "network/confirm/base_delete.html"

    def get_success_url(self):
        next = self.request.POST.get('next')
        if next:
            return next
        else:
            return reverse_lazy('network.rule_list')


class VlanList(SingleTableView):
    model = Vlan
    table_class = VlanTable
    template_name = "network/vlan-list.html"
    table_pagination = False


class VlanDetail(UpdateView):
    model = Vlan
    template_name = "network/vlan-edit.html"
    form_class = VlanForm
    slug_field = 'vid'
    slug_url_kwarg = 'vid'

    def get_context_data(self, **kwargs):
        context = super(VlanDetail, self).get_context_data(**kwargs)
        q = Host.objects.filter(vlan=self.object).all()
        context['host_list'] = SmallHostTable(q)
        context['vlan_vid'] = self.kwargs.get('vid')
        return context

    success_url = reverse_lazy('network.vlan_list')


class VlanCreate(CreateView):
    model = Vlan
    template_name = "network/vlan-create.html"
    form_class = VlanForm


class VlanDelete(DeleteView):
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
            messages.error(request, _("Object name does not match!"))
            return self.get(request, *args, **kwargs)

        response = super(VlanDelete, self).delete(request, *args, **kwargs)
        messages.success(request, _("Vlan successfully deleted!"))
        return response

    def get_context_data(self, **kwargs):
        context = super(VlanDelete, self).get_context_data(**kwargs)

        deps = []
        # hosts
        hosts = Host.objects.filter(vlan=self.get_object).all()
        if len(hosts) > 0:
            deps.append({
                'name': 'Hosts',
                'data': hosts
            })

            # records
            records = Record.objects.filter(host__in=deps[0]['data'])
            if len(records) > 0:
                deps.append({
                    'name': 'Records',
                    'data':  records
                })

        context['deps'] = deps
        context['confirmation'] = True
        return context


class VlanGroupList(SingleTableView):
    model = VlanGroup
    table_class = VlanGroupTable
    template_name = "network/vlan-group-list.html"
    table_pagination = False


class VlanGroupDetail(UpdateView):
    model = VlanGroup
    template_name = "network/vlan-group-edit.html"
    form_class = VlanGroupForm

    success_url = reverse_lazy('network.vlan_group_list')

    def get_context_data(self, *args, **kwargs):
        context = super(VlanGroupDetail, self).get_context_data(**kwargs)
        context['vlangroup_pk'] = self.object.pk
        return context


class VlanGroupCreate(CreateView):
    model = VlanGroup
    template_name = "network/vlan-group-create.html"
    form_class = VlanGroupForm


class VlanGroupDelete(DeleteView):
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
        return redirect(reverse_lazy('network.host',
                                     kwargs={'pk': kwargs['pk']}))


def add_host_group(request, **kwargs):
    group_pk = request.POST.get('group')
    if request.method == "POST" and group_pk:
        host = Host.objects.get(pk=kwargs['pk'])
        group = Group.objects.get(pk=group_pk)
        host.groups.add(group)
        return redirect(reverse_lazy('network.host', kwargs=kwargs))
