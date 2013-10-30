from django.http import HttpResponse
from django.views.generic import TemplateView, DetailView
from django_tables2 import SingleTableView

from tables import VmListTable

from vm.models import Instance, InstanceTemplate, InterfaceTemplate
from firewall.models import Vlan
from storage.models import Disk
from django.core import signing
from os import getenv

import json


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

        context.update({
            'running_vms': instances.filter(state='RUNNING'),
            'running_vm_num': instances.filter(state='RUNNING').count(),
            'stopped_vm_num': instances.exclude(
                state__in=['RUNNING', 'NOSTATE']).count()
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
            host = str(instance.node.host.ipv4)
            value = signing.dumps({'host': host,
                                   'port': port},
                                  key=getenv("PROXY_SECRET", 'asdasd')),
            context.update({
                'vnc_url': '%s' % value
            })
        return context


class TemplateDetail(DetailView):
    model = InstanceTemplate

    def get(self, request, *args, **kwargs):
        if request.is_ajax():
            template = InstanceTemplate.objects.get(pk=kwargs['pk'])
            template = {
                'num_cores': template.num_cores,
                'ram_size': template.ram_size,
                'priority': template.priority,
                'arch': template.arch,
                'description': template.description,
                'system': template.system,
                'name': template.name,
                'disks': [{'pk': d.pk, 'name': d.name}
                          for d in template.disks.all()],
                'network': [
                    {'vlan_pk': i.vlan.pk, 'vlan': i.vlan.name,
                     'managed': i.managed}
                    for i in InterfaceTemplate.objects.filter(
                        template=self.get_object()).all()
                ]
            }
            return HttpResponse(json.dumps(template),
                                content_type="application/json")
        else:
            # return super(TemplateDetail, self).get(request, *args, **kwargs)
            return HttpResponse('soon')


class VmList(SingleTableView):
    template_name = "dashboard/vm-list.html"
    model = Instance
    table_class = VmListTable
    table_pagination = False


class VmCreate(TemplateView):

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/modal-wrapper.html']
        else:
            return ['dashboard/nojs-wrapper.html']

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context.update({
            'template': 'dashboard/vm-create.html',
            'box_title': 'Create a VM'
        })
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super(VmCreate, self).get_context_data(**kwargs)
        # TODO acl
        context.update({
            'templates': InstanceTemplate.objects.all(),
            'vlans': Vlan.objects.all(),
            'disks': Disk.objects.exclude(type="qcow2-snap")
        })

        return context

    def post(self, request, *args, **kwargs):
        if self.request.user.is_authenticated():
            user = self.request.user
        else:
            user = None

        resp = request.POST.copy()
        resp['managed-vlans'] = request.POST.getlist('managed-vlans')
        resp['unmanaged-vlans'] = request.POST.getlist('unmanaged-vlans')
        resp['disks'] = request.POST.getlist('disks')

        template = InstanceTemplate.objects.get(
            pk=request.POST.get('template-pk'))
        inst = Instance.create_from_template(template=template, owner=user)
        inst.deploy_async()

        # TODO handle response
        return HttpResponse(json.dumps(resp), content_type="application/json")
