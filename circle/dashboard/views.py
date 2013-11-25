from os import getenv
import json
import logging
import re

from django.contrib.auth.models import User, Group
from django.contrib.messages import warning
from django.core.exceptions import PermissionDenied
from django.core import signing
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django.views.generic.detail import SingleObjectMixin
from django.views.generic import TemplateView, DetailView, View, DeleteView
from django.contrib import messages
from django.utils.translation import ugettext as _

from django_tables2 import SingleTableView

from .tables import VmListTable
from vm.models import (Instance, InstanceTemplate, InterfaceTemplate,
                       InstanceActivity)
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

        instances = Instance.active.filter(owner=user)
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


class CheckedDetailView(DetailView):
    read_level = 'user'

    def get_context_data(self, **kwargs):
        context = super(CheckedDetailView, self).get_context_data(**kwargs)
        instance = context['instance']
        if not instance.has_level(self.request.user, self.read_level):
            raise PermissionDenied()
        return context


class VmDetailView(CheckedDetailView):
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

        # activity data
        ia = InstanceActivity.objects.filter(
            instance=self.object, parent=None
        ).order_by('-started').select_related()

        context['activity'] = ia
        context['acl'] = get_acl_data(instance)
        return context

    def post(self, request, *args, **kwargs):
        if (request.POST.get('ram-size') and request.POST.get('cpu-count')
                and request.POST.get('cpu-priority')):
            return self.__set_resources(request)

        # this is usually not None so it should be the last
        if request.POST.get('new_name'):
            return self.__set_name(request)

    def __set_resources(self, request):
        self.object = self.get_object()
        if not self.object.has_level(request.user, 'owner'):
            raise PermissionDenied()

        resources = {
            'num_cores': request.POST.get('cpu-count'),
            'ram_size': request.POST.get('ram-size'),
            'priority': request.POST.get('cpu-priority')
        }
        Instance.objects.filter(pk=self.object.pk).update(**resources)

        success_message = _("Resources successfully updated!")
        if request.is_ajax():
            response = {'message': success_message}
            return HttpResponse(
                json.dumps(response),
                content_type="application/json"
            )
        else:
            messages.success(request, success_message)
            return redirect(reverse_lazy("dashboard.views.detail",
                                         kwargs={'pk': self.object.pk}))

    def __set_name(self, request):
        self.object = self.get_object()
        new_name = request.POST.get("new_name")
        Instance.objects.filter(pk=self.object.pk).update(
            **{'name': new_name})

        success_message = _("VM successfully renamed!")
        if request.is_ajax():
            response = {
                'message': success_message,
                'new_name': new_name,
                'vm_pk': self.object.pk
            }
            return HttpResponse(
                json.dumps(response),
                content_type="application/json"
            )
        else:
            messages.success(request, success_message)
            return redirect(reverse_lazy("dashboard.views.detail",
                                         kwargs={'pk': self.object.pk}))


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
    queryset = Instance.active.all()
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

    # TODO handle not ajax posts
    def post(self, request, *args, **kwargs):
        if self.request.user.is_authenticated():
            user = self.request.user
        else:
            user = None

        resp = {}
        try:
            ikwargs = {
                'num_cores': int(request.POST.get('cpu-count')),
                'ram_size': int(request.POST.get('ram-size')),
                'priority': int(request.POST.get('cpu-priority')),
            }

            networks = [InterfaceTemplate(vlan=Vlan.objects.get(pk=l),
                                          managed=True)
                        for l in request.POST.getlist('managed-vlans')
                        ]
            networks.extend([InterfaceTemplate(vlan=Vlan.objects.get(pk=l),
                                               managed=False)
                            for l in request.POST.getlist('unmanaged-vlans')
                             ])

            disks = Disk.objects.filter(pk__in=request.POST.getlist('disks'))
            template = InstanceTemplate.objects.get(
                pk=request.POST.get('template-pk'))

            inst = Instance.create_from_template(template=template,
                                                 owner=user, networks=networks,
                                                 disks=disks, **ikwargs)
            inst.deploy_async(user=request.user)

            resp['pk'] = inst.pk
            messages.success(request, _('VM successfully created!'))
        except InstanceTemplate.DoesNotExist:
            resp['error'] = True
        except Exception, e:
            print e
            resp['error'] = True

        if request.is_ajax():
            return HttpResponse(json.dumps(resp),
                                content_type="application/json",
                                status=500 if resp.get('error') else 200)
        else:
            return redirect(reverse_lazy('dashboard.views.detail', resp))


class VmDelete(DeleteView):
    model = Instance
    template_name = "dashboard/confirm/base-delete.html"

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/confirm/ajax-delete.html']
        else:
            return ['dashboard/confirm/base-delete.html']

    def get_context_data(self, **kwargs):
        # this is redundant now, but if we wanna add more to print
        # we'll need this
        context = super(VmDelete, self).get_context_data(**kwargs)
        return context

    # github.com/django/django/blob/master/django/views/generic/edit.py#L245
    def delete(self, request, *args, **kwargs):
        object = self.get_object()
        if not object.has_level(request.user, 'owner'):
            raise PermissionDenied()

        object.destroy_async(user=request.user)
        success_url = self.get_success_url()
        success_message = _("VM successfully deleted!")

        if request.is_ajax():
            if request.POST.get('redirect').lower() == "true":
                messages.success(request, success_message)
            return HttpResponse(
                json.dumps({'message': success_message}),
                content_type="application/json",
            )
        else:
            messages.success(request, success_message)
            return HttpResponseRedirect(success_url)

    def get_success_url(self):
        next = self.request.POST.get('next')
        if next:
            return next
        else:
            return reverse_lazy('dashboard.index')


class VmMassDelete(View):
    def get(self, request, *args, **kwargs):
        vms = request.GET.getlist('v[]')
        objects = Instance.objects.filter(pk__in=vms)
        return render(request, "dashboard/confirm/mass-delete.html",
                      {'objects': objects})

    def post(self, request, *args, **kwargs):
        vms = request.POST.getlist('vms')
        names = []
        if vms is not None:
            for i in Instance.objects.filter(pk__in=vms):
                if not i.has_level(request.user, 'owner'):
                    logger.info('Tried to delete instance #%d without owner '
                                'permission by %s.', i.pk,
                                unicode(request.user))
                    raise PermissionDenied()  # no need for rollback or proper
                                            # error message, this can't
                                            # normally happen.
                i.destroy_async(request.user)
                names.append(i.name)

        success_message = _("Mass delete complete, the following VMs were " +
                            "deleted: %s!" % u', '.join(names))

        # we can get this only via AJAX ...
        if request.is_ajax():
            return HttpResponse(
                json.dumps({'message': success_message}),
                content_type="application/json"
            )
        else:
            messages.success(request, success_message)
            next = request.GET.get('next')
            return redirect(next if next else reverse_lazy('dashboard.index'))


@require_POST
def vm_activity(request, pk):
    object = Instance.objects.get(pk=pk)
    if not object.has_level(request.user, 'owner'):
        raise PermissionDenied()

    latest = request.POST.get('latest')
    latest_sub = request.POST.get('latest_sub')

    instance = Instance.objects.get(pk=pk)
    new_sub_activities = InstanceActivity.objects.filter(
        parent=latest, pk__gt=latest_sub,
        instance=instance)
    # new_activities = InstanceActivity.objects.filter(
    #     parent=None, instance=instance, pk__gt=latest).values('finished')
    latest_sub_finished = InstanceActivity.objects.get(pk=latest_sub).finished

    time_string = "%H:%M:%S"
    new_sub_activities = [
        {'name': a.get_readable_name(), 'id': a.pk,
         'finished': None if a.finished is None else a.finished.strftime(
             time_string
         )
         } for a in new_sub_activities
    ]

    response = {
        'new_sub_activities': new_sub_activities,
        # TODO 'new_acitivites': new_activities,
        'is_parent_finished': True if InstanceActivity.objects.get(
            pk=latest).finished is not None else False,
        'latest_sub_finished': None if latest_sub_finished is None else
        latest_sub_finished.strftime(time_string)
    }

    return HttpResponse(
        json.dumps(response),
        content_type="application/json"
    )
