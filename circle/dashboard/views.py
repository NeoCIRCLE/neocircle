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

        instances = Instance.objects.filter(owner=user)
        context = super(IndexView, self).get_context_data(**kwargs)
        context.update({
            'instances': instances[:5],
            'more_instances': instances.count() - len(instances[:5])
        })

        stopped_vm_states = ['PAUSED', 'SHUTDOWN', 'SHUTOFF']
        context.update({
            'running_vms': instances.filter(state='RUNNING'),
            'running_vm_num': instances.filter(state='RUNNING').count(),
            'stopped_vm_num': instances.filter(
                state__in=stopped_vm_states).count()
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
    table_pagination = False


class VmCreate(TemplateView):

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/vm-create.html']
        else:
            return ['dashboard/ajax-wrapper.html']

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if not request.is_ajax():
            context.update({
                'template': 'dashboard/vm-create.html',
                'box_title': 'Create a VM'
            })
        return self.render_to_response(context)
