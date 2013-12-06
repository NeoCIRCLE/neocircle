from os import getenv
import json
import logging
import re

from django.contrib.auth.models import User, Group
from django.contrib.messages import warning
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.core import signing
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django.views.generic.detail import SingleObjectMixin
from django.views.generic import TemplateView, DetailView, View, DeleteView
from django.contrib import messages
from django.utils.translation import ugettext as _

from django_tables2 import SingleTableView
from braces.views import LoginRequiredMixin

from .tables import (VmListTable, NodeListTable)
from vm.models import (Instance, InstanceTemplate, InterfaceTemplate,
                       InstanceActivity, Node, instance_activity)
from firewall.models import Vlan, Host, Rule
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

        nodes = Node.objects.all()
        context.update({
            'nodes': nodes[:1],
            'more_nodes': nodes.count() - len(nodes[:1])
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

        if request.POST.get('new_name'):
            return self.__set_name(request)

        if request.POST.get('new_tag') is not None:
            return self.__add_tag(request)

        if request.POST.get("to_remove") is not None:
            return self.__remove_tag(request)

        if request.POST.get("port") is not None:
            return self.__add_port(request)

    def __set_resources(self, request):
        self.object = self.get_object()
        if not self.object.has_level(request.user, 'owner'):
            raise PermissionDenied()
        if not request.user.has_perm('vm.change_resources'):
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

    def __add_tag(self, request):
        new_tag = request.POST.get('new_tag')
        self.object = self.get_object()

        if len(new_tag) < 1:
            message = u"Please input something!"
        elif len(new_tag) > 20:
            message = u"Tag name is too long!"
        else:
            self.object.tags.add(new_tag)

        try:
            messages.error(request, message)
        except:
            pass

        return redirect(reverse_lazy("dashboard.views.detail",
                                     kwargs={'pk': self.object.pk}))

    def __remove_tag(self, request):
        try:
            to_remove = request.POST.get('to_remove')
            self.object = self.get_object()

            self.object.tags.remove(to_remove)
            message = u"Success"
        except:  # note this won't really happen
            message = u"Not success"

        if request.is_ajax():
            return HttpResponse(
                json.dumps({'message': message}),
                content_type="application=json"
            )

    def __add_port(self, request):
        object = self.get_object()
        if not object.has_level(request.user, 'owner'):
            raise PermissionDenied()
        if not request.user.has_perm('vm.config_ports'):
            raise PermissionDenied()

        port = request.POST.get("port")
        proto = request.POST.get("proto")

        try:
            error = None
            host = Host.objects.get(pk=request.POST.get("host_pk"))
            host.add_port(proto, private=port)
        except Host.DoesNotExist:
            error = _("Host not found!")
        except Exception, e:
            error = u', '.join(e.messages)

        if request.is_ajax():
            pass
        else:
            if error:
                messages.error(request, error)
            return redirect(reverse_lazy("dashboard.views.detail",
                                         kwargs={'pk': self.get_object().pk}))


class NodeDetailView(DetailView):
    template_name = "dashboard/node-detail.html"
    model = Node

    def get_context_data(self, **kwargs):
        context = super(NodeDetailView, self).get_context_data(**kwargs)
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
    queryset = Instance.active.all()
    table_class = VmListTable
    table_pagination = False


class NodeList(SingleTableView):
    template_name = "dashboard/node-list.html"
    model = Node
    table_class = NodeListTable
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
        print kwargs
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


class PortDelete(DeleteView):
    model = Rule
    pk_url_kwarg = 'rule'

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/confirm/ajax-delete.html']
        else:
            return ['dashboard/confirm/base-delete.html']

    def get_context_data(self, **kwargs):
        context = super(PortDelete, self).get_context_data(**kwargs)
        rule = kwargs.get('object')
        instance = rule.host.interface_set.get().instance
        context['title'] = _("Port delete confirmation")
        context['text'] = _("Are you sure you want to close %(port)d/"
                            "%(proto)s on %(vm)s?" % {'port': rule.dport,
                                                      'proto': rule.proto,
                                                      'vm': instance})
        return context

    def delete(self, request, *args, **kwargs):
        rule = Rule.objects.get(pk=kwargs.get("rule"))
        instance = rule.host.interface_set.get().instance
        if not instance.has_level(request.user, 'owner'):
            raise PermissionDenied()

        super(PortDelete, self).delete(request, *args, **kwargs)

        success_url = self.get_success_url()
        success_message = _("Port successfully removed!")

        if request.is_ajax():
            return HttpResponse(
                json.dumps({'message': success_message}),
                content_type="application/json",
            )
        else:
            messages.success(request, success_message)
            return HttpResponseRedirect("%s#network" % success_url)

    def get_success_url(self):
        return reverse_lazy('dashboard.views.detail',
                            kwargs={'pk': self.kwargs.get("pk")})


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


class TransferOwnershipView(LoginRequiredMixin, DetailView):
    model = Instance
    template_name = 'dashboard/vm-detail-tx-owner.html'

    def post(self, request, *args, **kwargs):
        try:
            new_owner = User.objects.get(username=request.POST['name'])
        except User.DoesNotExist:
            raise Http404()
        except KeyError:
            raise SuspiciousOperation()

        obj = self.get_object()
        if not (obj.owner == request.user or
                request.user.is_superuser):
            raise PermissionDenied()

        token = signing.dumps((obj.pk, new_owner.pk),
                              salt=TransferOwnershipConfirmView.get_salt())
        return HttpResponse("%s?key=%s" % (
            reverse('dashboard.views.vm-transfer-ownership-confirm'), token),
            content_type="text/plain")


class TransferOwnershipConfirmView(LoginRequiredMixin, View):
    max_age = 3 * 24 * 3600
    success_message = _("Ownership successfully transferred.")

    @classmethod
    def get_salt(cls):
        return unicode(cls)

    def get(self, request, *args, **kwargs):
        """Confirm ownership transfer based on token.
        """
        try:
            key = request.GET['key']
            logger.debug('Confirm dialog for token %s.', key)
            instance, new_owner = self.get_instance(key, request.user)
        except KeyError:
            raise Http404()
        except PermissionDenied():
            messages.error(request, _('This token is for an other user.'))
            raise
        except SuspiciousOperation:
            messages.error(request, _('This token is invalid or has expired.'))
            raise PermissionDenied()
        return render(request,
                      "dashboard/confirm/base-transfer-ownership.html",
                      dictionary={'instance': instance, 'key': key})

    def post(self, request, *args, **kwargs):
        """Really transfer ownership based on token.
        """
        try:
            key = request.POST['key']
            instance, owner = self.get_instance(key, request.user)
        except KeyError:
            logger.debug('Posted to %s without key field.',
                         unicode(self.__class__))
            raise SuspiciousOperation()

        old = instance.owner
        with instance_activity(code_suffix='ownership-transferred',
                               instance=instance, user=request.user):
            instance.owner = request.user
            instance.clean()
            instance.save()
        messages.success(request, self.success_message)
        logger.info('Ownership of %s transferred from %s to %s.',
                    unicode(instance), unicode(old), unicode(request.user))
        return HttpResponseRedirect(instance.get_absolute_url())

    def get_instance(self, key, user):
        """Get object based on signed token.
        """
        try:
            instance, new_owner = (
                signing.loads(key, max_age=self.max_age,
                              salt=self.get_salt()))
        except signing.BadSignature as e:
            logger.error('Tried invalid token. Token: %s, user: %s. %s',
                         key, unicode(user), unicode(e))
            raise SuspiciousOperation()
        except ValueError as e:
            logger.error('Tried invalid token. Token: %s, user: %s. %s',
                         key, unicode(user), unicode(e))
            raise SuspiciousOperation()
        except TypeError as e:
            logger.error('Tried invalid token. Token: %s, user: %s. %s',
                         key, unicode(user), unicode(e))
            raise SuspiciousOperation()

        try:
            instance = Instance.objects.get(id=instance)
        except Instance.DoesNotExist as e:
            logger.error('Tried token to nonexistent instance %d. '
                         'Token: %s, user: %s. %s',
                         instance, key, unicode(user), unicode(e))
            raise Http404()

        if new_owner != user.pk:
            logger.error('%s (%d) tried the token for %s. Token: %s.',
                         unicode(user), user.pk, new_owner, key)
            raise PermissionDenied()
        return (instance, new_owner)
