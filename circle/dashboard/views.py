from django.views.generic import TemplateView, DetailView
from django_tables2 import SingleTableView

from tables import VmListTable

from vm.models import Instance
from django.core import signing


class IndexView(TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        if self.request.user.is_authenticated():
            user = self.request.user
        else:
            user = None

        context = super(IndexView, self).get_context_data(**kwargs)
        context.update({
            'instances': Instance.objects.filter(owner=user),
        })
        return context


class VmDetailView(DetailView):
    template_name = "dashboard/vm-detail.html"
    queryset = Instance.objects.all()

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        instance = context['instance']
        if instance.node:
            port = instance.vnc_port
            host = instance.node.host.ipv4
            value = signing.dumps({'host': host,
                                   'port': port}, key='asdasd')
            context.update({
                'vnc_url': '%s' % value
            })
        return context


class VmList(SingleTableView):
    template_name = "dashboard/vm-list.html"
    model = Instance
    table_class = VmListTable
