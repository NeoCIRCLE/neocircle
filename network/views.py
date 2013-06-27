from django.views.generic import TemplateView
from django.views.generic import UpdateView

from django_tables2 import SingleTableView

from firewall.models import Host
from .tables import HostTable


class IndexView(TemplateView):
    template_name = "network/index.html"


class HostList(SingleTableView):
    model = Host
    table_class = HostTable
    template_name = "network/host-list.html"


class HostDetail(UpdateView):
    model = Host
    template_name = "network/host-edit.html"
