from django.views.generic import TemplateView
from django.views.generic import UpdateView
from django.core.urlresolvers import reverse_lazy

from django_tables2 import SingleTableView

from firewall.models import Host, Vlan
from .tables import HostTable, VlanTable, SmallHostTable
from .forms import HostForm, VlanForm


class IndexView(TemplateView):
    template_name = "network/index.html"


class HostList(SingleTableView):
    model = Host
    table_class = HostTable
    template_name = "network/host-list.html"


class HostDetail(UpdateView):
    model = Host
    template_name = "network/host-edit.html"
    form_class = HostForm

    def get_success_url(self):
        if 'pk' in self.kwargs:
            return reverse_lazy('network.host', kwargs=self.kwargs)


class VlanList(SingleTableView):
    model = Vlan
    table_class = VlanTable
    template_name = "network/vlan-list.html"


class VlanDetail(UpdateView):
    model = Vlan
    template_name = "network/vlan-edit.html"
    form_class = VlanForm

    def get_context_data(self, **kwargs):
        context = super(VlanDetail, self).get_context_data(**kwargs)
        q = Host.objects.filter(vlan=self.object).all()
        context['host_list'] = SmallHostTable(q)
        return context

    success_url = reverse_lazy('network.vlan_list')
