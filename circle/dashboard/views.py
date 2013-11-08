from os import getenv
import json
import logging
import re

from django.contrib.auth.models import User, Group
from django.contrib.messages import warning
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView, DetailView, View
from django.views.generic.detail import SingleObjectMixin
from django.http import HttpResponse

from django_tables2 import SingleTableView

from .tables import VmListTable
from vm.models import Instance, InstanceTemplate, InterfaceTemplate
from firewall.models import Vlan
from storage.models import Disk

logger = logging.getLogger(__name__)


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


def get_acl_data(obj):
    levels = obj.ACL_LEVELS
    users = obj.get_users_with_level()
    users = [{'user': u, 'level': l} for u, l in users]
    groups = obj.get_groups_with_level()
    groups = [{'group': g, 'level': l} for g, l in groups]
    return {'users': users, 'groups': groups, 'levels': levels,
            'url': reverse('dashboard.views.vm-acl', args=[obj.pk])}


class VmDetailView(DetailView):
    template_name = "dashboard/vm-detail.html"
    model = Instance

    def get_context_data(self, **kwargs):
        context = super(VmDetailView, self).get_context_data(**kwargs)
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
        context['acl'] = get_acl_data(instance)
        return context


class AclUpdateView(View, SingleObjectMixin):

    def post(self, request, *args, **kwargs):
        instance = self.get_object()
        if not (instance.has_level(request.user, "owner") or
                getattr(instance, 'owner', None) == request.user):
            logger.warning('Tried to set permissions of %s by non-owner %s.',
                           unicode(instance), unicode(request.user))
            raise PermissionDenied()
        self.set_levels(request, instance)
        self.add_levels(request, instance)
        return redirect(instance)

    def set_levels(self, request, instance):
        for key, value in request.POST.items():
            m = re.match('perm-([ug])-(\d+)', key)
            if m:
                type, id = m.groups()
                entity = {'u': User, 'g': Group}[type].objects.get(id=id)
                instance.set_level(entity, value)
                logger.info("Set %s's acl level for %s to %s by %s.",
                            unicode(entity), unicode(instance),
                            value, unicode(request.user))

    def add_levels(self, request, instance):
        name = request.POST['perm-new-name']
        value = request.POST['perm-new']
        if not name:
            return
        try:
            entity = User.objects.get(username=name)
        except User.DoesNotExist:
            entity = None
            try:
                entity = Group.objects.get(name=name)
            except Group.DoesNotExist:
                warning(request, _('User or group "%s" not found.') % name)
                return

        instance.set_level(entity, value)
        logger.info("Set %s's new acl level for %s to %s by %s.",
                    unicode(entity), unicode(instance),
                    value, unicode(request.user))


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
