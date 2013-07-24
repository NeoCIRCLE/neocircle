from django.views.generic import TemplateView
from django.views.generic import UpdateView
from django.core.urlresolvers import reverse_lazy

from django_tables2 import SingleTableView

from firewall.models import Host, Vlan, Domain, Group, Record, Blacklist
from .tables import (HostTable, VlanTable, SmallHostTable, DomainTable,
                     GroupTable, RecordTable, BlacklistTable)
from .forms import (HostForm, VlanForm, DomainForm, GroupForm, RecordForm,
                    BlacklistForm)


class IndexView(TemplateView):
    template_name = "network/index.html"


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


class GroupList(SingleTableView):
    model = Group
    table_class = GroupTable
    template_name = "network/group-list.html"
    table_pagination = False


class GroupDetail(UpdateView):
    model = Group
    template_name = "network/group-edit.html"
    form_class = GroupForm

    def get_success_url(self):
        if 'pk' in self.kwargs:
            return reverse_lazy('network.group', kwargs=self.kwargs)


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
        print vlan_id
        if vlan_id:
            data = Host.objects.filter(vlan=vlan_id).all()
        else:
            data = Host.objects.all()

        return data


class HostDetail(UpdateView):
    model = Host
    template_name = "network/host-edit.html"
    form_class = HostForm

    def get_success_url(self):
        if 'pk' in self.kwargs:
            return reverse_lazy('network.host', kwargs=self.kwargs)


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
        q = Record.objects.get(pk=self.object.pk).fqdn
        context['fqdn'] = q
        return context

    def get_success_url(self):
        if 'pk' in self.kwargs:
            return reverse_lazy('network.record', kwargs=self.kwargs)


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
        return context

    success_url = reverse_lazy('network.vlan_list')
