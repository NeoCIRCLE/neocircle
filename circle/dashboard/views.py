from os import getenv
import json
import logging
import re
from datetime import datetime
import requests

from django.contrib.auth.models import User, Group
from django.contrib.messages import warning
from django.core.exceptions import (
    PermissionDenied, SuspiciousOperation,
)
from django.core import signing
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET
from django.views.generic.detail import SingleObjectMixin
from django.views.generic import (TemplateView, DetailView, View, DeleteView,
                                  UpdateView, CreateView)
from django.contrib import messages
from django.utils.translation import ugettext as _
from django.template.defaultfilters import title
from django.template.loader import render_to_string

from django.forms.models import inlineformset_factory
from django_tables2 import SingleTableView
from braces.views import LoginRequiredMixin, SuperuserRequiredMixin

from .forms import (
    VmCustomizeForm, TemplateForm, LeaseForm, NodeForm, HostForm,
    DiskAddForm,
)
from .tables import (VmListTable, NodeListTable, NodeVmListTable,
                     TemplateListTable, LeaseListTable, GroupListTable,)
from vm.models import (Instance, InstanceTemplate, InterfaceTemplate,
                       InstanceActivity, Node, instance_activity, Lease,
                       Interface, NodeActivity)
from firewall.models import Vlan, Host, Rule
from dashboard.models import Favourite

logger = logging.getLogger(__name__)


# github.com/django/django/blob/stable/1.6.x/django/contrib/messages/views.py
class SuccessMessageMixin(object):
    """
    Adds a success message on successful form submission.
    """
    success_message = ''

    def form_valid(self, form):
        response = super(SuccessMessageMixin, self).form_valid(form)
        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            messages.success(self.request, success_message)
        return response

    def get_success_message(self, cleaned_data):
        return self.success_message % cleaned_data


class IndexView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        if self.request.user.is_authenticated():
            user = self.request.user
        else:
            user = None
        context = super(IndexView, self).get_context_data(**kwargs)

        favs = Instance.objects.filter(favourite__user=self.request.user)
        instances = Instance.get_objects_with_level(
            'user', user).filter(destroyed=None)
        display = list(favs) + list(set(instances) - set(favs))
        for d in display:
            d.fav = True if d in favs else False
        context.update({
            'instances': display[:5],
            'more_instances': instances.count() - len(instances[:5])
        })

        nodes = Node.objects.all()
        groups = Group.objects.all()
        context.update({
            'nodes': nodes[:10],
            'more_nodes': nodes.count() - len(nodes[:10]),
            'groups': groups[:10],
            'more_groups': groups.count() - len(groups[:10]),
            'sum_node_num': nodes.count(),
            'node_num': {
                'running': Node.get_state_count(True, True),
                'missing': Node.get_state_count(False, True),
                'disabled': Node.get_state_count(True, False),
                'offline': Node.get_state_count(False, False)
            }
        })

        running = [i for i in instances if i.state == 'RUNNING']
        stopped = [i for i in instances if i.state not in ['RUNNING',
                                                           'NOSTATE']]
        context.update({
            'running_vms': running,
            'running_vm_num': len(running),
            'stopped_vm_num': len(stopped)
        })

        context['templates'] = InstanceTemplate.objects.all()[:5]
        return context


def get_vm_acl_data(obj):
    levels = obj.ACL_LEVELS
    users = obj.get_users_with_level()
    users = [{'user': u, 'level': l} for u, l in users]
    groups = obj.get_groups_with_level()
    groups = [{'group': g, 'level': l} for g, l in groups]
    return {'users': users, 'groups': groups, 'levels': levels,
            'url': reverse('dashboard.views.vm-acl', args=[obj.pk])}


def get_group_acl_data(obj):
    aclobj = obj.profile
    levels = aclobj.ACL_LEVELS
    users = aclobj.get_users_with_level()
    users = [{'user': u, 'level': l} for u, l in users]
    groups = aclobj.get_groups_with_level()
    groups = [{'group': g, 'level': l} for g, l in groups]
    return {'users': users, 'groups': groups, 'levels': levels,
            'url': reverse('dashboard.views.group-acl', args=[obj.pk])}


class CheckedDetailView(LoginRequiredMixin, DetailView):
    read_level = 'user'

    def get_has_level(self):
        return self.object.has_level

    def get_context_data(self, **kwargs):
        context = super(CheckedDetailView, self).get_context_data(**kwargs)
        if not self.get_has_level()(self.request.user, self.read_level):
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
                'graphite_enabled': VmGraphView.get_graphite_url() is not None,
                'vnc_url': '%s' % value
            })

        # activity data
        ia = InstanceActivity.objects.filter(
            instance=self.object, parent=None
        ).order_by('-started').select_related()
        context['activities'] = ia

        context['vlans'] = Vlan.get_objects_with_level(
            'user', self.request.user
        ).exclude(
            pk__in=Interface.objects.filter(
                instance=self.get_object()).values_list("vlan", flat=True)
        ).all()
        context['acl'] = get_vm_acl_data(instance)
        context['forms'] = {
            'disk_add_form': DiskAddForm(prefix="disk"),
        }
        context['os_type_icon'] = instance.os_type.replace("unknown",
                                                           "question")
        return context

    def post(self, request, *args, **kwargs):
        if (request.POST.get('ram-size') and request.POST.get('cpu-count')
                and request.POST.get('cpu-priority')):
            return self.__set_resources(request)

        options = {
            'change_password': self.__change_password,
            'new_name': self.__set_name,
            'new_tag': self.__add_tag,
            'to_remove': self.__remove_tag,
            'port': self.__add_port,
            'new_network_vlan': self.__new_network,
            'save_as': self.__save_as,
            'disk-name': self.__add_disk,
            'shut_down': self.__shut_down,
            'sleep': self.__sleep,
            'wake_up': self.__wake_up,
            'deploy': self.__deploy,
            'reset': self.__reset,
            'reboot': self.__reboot,
        }
        for k, v in options.iteritems():
            if request.POST.get(k) is not None:
                return v(request)

    def __change_password(self, request):
        self.object = self.get_object()
        if not self.object.has_level(request.user, 'owner'):
            raise PermissionDenied()

        self.object.change_password(user=request.user)
        messages.success(request, _("Password changed!"))
        if request.is_ajax():
            return HttpResponse("Success!")
        else:
            return redirect(reverse_lazy("dashboard.views.detail",
                                         kwargs={'pk': self.object.pk}))

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
        if not self.object.has_level(request.user, 'owner'):
            raise PermissionDenied()
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
        if not self.object.has_level(request.user, 'owner'):
            raise PermissionDenied()

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
            if not self.object.has_level(request.user, 'owner'):
                raise PermissionDenied()

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
        if (not object.has_level(request.user, 'owner') or
                not request.user.has_perm('vm.config_ports')):
            raise PermissionDenied()

        port = request.POST.get("port")
        proto = request.POST.get("proto")

        try:
            error = None
            host = Host.objects.get(pk=request.POST.get("host_pk"))
            host.add_port(proto, private=port)
        except ValueError:
            error = _("There is a problem with your input!")
        except Exception, e:
            error = u', '.join(e.messages)

        if request.is_ajax():
            pass
        else:
            if error:
                messages.error(request, error)
            return redirect(reverse_lazy("dashboard.views.detail",
                                         kwargs={'pk': self.get_object().pk}))

    def __new_network(self, request):
        self.object = self.get_object()
        if not self.object.has_level(request.user, 'owner'):
            raise PermissionDenied()

        vlan = Vlan.objects.get(pk=request.POST.get("new_network_vlan"))
        if not vlan.has_level(request.user, 'user'):
            raise PermissionDenied()
        try:
            Interface.create(vlan=vlan, instance=self.object,
                             managed=vlan.managed, owner=request.user)
            messages.success(request, _("Successfully added new interface!"))
        except Exception, e:
            error = u' '.join(e.messages)
            messages.error(request, error)

        return redirect("%s#network" % reverse_lazy(
            "dashboard.views.detail", kwargs={'pk': self.object.pk}))

    def __save_as(self, request):
        self.object = self.get_object()
        if not self.object.has_level(request.user, 'owner'):
            raise PermissionDenied()

        date = datetime.now().strftime("%Y-%m-%d %H:%M")
        new_name = "Saved from %s (#%d) at %s" % (
            self.object.name, self.object.pk, date
        )
        template = self.object.save_as_template(name=new_name,
                                                owner=request.user)
        messages.success(request, _("Instance succesfully saved as template, "
                                    "please rename it!"))
        return redirect(reverse_lazy("dashboard.views.template-detail",
                                     kwargs={'pk': template.pk}))

    def __add_disk(self, request):
        self.object = self.get_object()
        if not self.object.has_level(request.user, 'owner'):
            raise PermissionDenied()

        form = DiskAddForm(request.POST, prefix="disk")
        if form.is_valid():
            messages.success(request, _("New disk successfully created!"))
            form.save(self.object)
        else:
            error = "<br /> ".join(["<strong>%s</strong>: %s" %
                                    (title(i[0]), i[1][0])
                                    for i in form.errors.items()])
            messages.error(request, error)

        return redirect("%s#resources" % reverse_lazy(
            "dashboard.views.detail", kwargs={'pk': self.object.pk}))

    def __shut_down(self, request):
        self.object = self.get_object()
        if not self.object.has_level(request.user, 'owner'):
            raise PermissionDenied()

        self.object.shutdown_async(request.user)
        return redirect("%s#activity" % self.object.get_absolute_url())

    def __sleep(self, request):
        self.object = self.get_object()
        if not self.object.has_level(request.user, 'owner'):
            raise PermissionDenied()

        self.object.sleep_async(request.user)
        return redirect("%s#activity" % self.object.get_absolute_url())

    def __wake_up(self, request):
        self.object = self.get_object()
        if not self.object.has_level(request.user, 'owner'):
            raise PermissionDenied()

        self.object.wake_up_async(request.user)
        return redirect("%s#activity" % self.object.get_absolute_url())

    def __deploy(self, request):
        self.object = self.get_object()
        if not self.object.has_level(request.user, 'owner'):
            raise PermissionDenied()

        self.object.deploy_async(request.user)
        return redirect("%s#activity" % self.object.get_absolute_url())

    def __reset(self, request):
        self.object = self.get_object()
        if not self.object.has_level(request.user, 'owner'):
            raise PermissionDenied()

        self.object.reset_async(request.user)
        return redirect("%s#activity" % self.object.get_absolute_url())

    def __reboot(self, request):
        self.object = self.get_object()
        if not self.object.has_level(request.user, 'owner'):
            raise PermissionDenied()

        self.object.reboot_async(request.user)
        return redirect("%s#activity" % self.object.get_absolute_url())


class NodeDetailView(LoginRequiredMixin, SuperuserRequiredMixin, DetailView):
    template_name = "dashboard/node-detail.html"
    model = Node

    def get_context_data(self, **kwargs):
        context = super(NodeDetailView, self).get_context_data(**kwargs)
        instances = Instance.active.filter(node=self.object)
        context['table'] = NodeVmListTable(instances)
        na = NodeActivity.objects.filter(
            node=self.object, parent=None
        ).order_by('-started').select_related()
        context['activities'] = na
        return context

    def post(self, request, *args, **kwargs):
        if request.POST.get('new_name'):
            return self.__set_name(request)
        if request.POST.get('new_status'):
            return self.__set_status(request)

    def __set_name(self, request):
        self.object = self.get_object()
        new_name = request.POST.get("new_name")
        Node.objects.filter(pk=self.object.pk).update(
            **{'name': new_name})

        success_message = _("Node successfully renamed!")
        if request.is_ajax():
            response = {
                'message': success_message,
                'new_name': new_name,
                'node_pk': self.object.pk
            }
            return HttpResponse(
                json.dumps(response),
                content_type="application/json"
            )
        else:
            messages.success(request, success_message)
            return redirect(reverse_lazy("dashboard.views.node-detail",
                                         kwargs={'pk': self.object.pk}))

    def __set_status(self, request):
        self.object = self.get_object()
        new_status = request.POST.get("new_status")
        if new_status == "enable":
            self.object.enable(user=request.user)
        elif new_status == "disable":
            self.object.disable(user=request.user)
        else:
            return

        success_message = _("Node successfully changed status!")
        if request.is_ajax():
            response = {
                'message': success_message,
                'new_status': new_status,
                'node_pk': self.object.pk
            }
            return HttpResponse(
                json.dumps(response),
                content_type="application/json"
            )
        else:
            messages.success(request, success_message)
            return redirect(reverse_lazy("dashboard.views.node-detail",
                                         kwargs={'pk': self.object.pk}))


class GroupDetailView(CheckedDetailView):
    template_name = "dashboard/group-detail.html"
    model = Group

    def get_has_level(self):
        return self.object.profile.has_level

    def get_context_data(self, **kwargs):
        context = super(GroupDetailView, self).get_context_data(**kwargs)
        context['group'] = self.object
        context['users'] = self.object.user_set.all()
        context['acl'] = get_group_acl_data(self.object)
        return context

    def post(self, request, *args, **kwargs):

        if request.POST.get('new_name'):
            return self.__set_name(request)

    def __set_name(self, request):
        self.object = self.get_object()
        new_name = request.POST.get("new_name")
        Group.objects.filter(pk=self.object.pk).update(
            **{'name': new_name})

        success_message = _("Group successfully renamed!")
        if request.is_ajax():
            response = {
                'message': success_message,
                'new_name': new_name,
                'group_pk': self.object.pk
            }
            return HttpResponse(
                json.dumps(response),
                content_type="application/json"
            )
        else:
            messages.success(request, success_message)
            return redirect(reverse_lazy("dashboard.views.group-detail",
                                         kwargs={'pk': self.object.pk}))


class AclUpdateView(LoginRequiredMixin, View, SingleObjectMixin):

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
                typ, id = m.groups()
                entity = {'u': User, 'g': Group}[typ].objects.get(id=id)
                if getattr(instance, "owner", None) == entity:
                    logger.info("Tried to set owner's acl level for %s by %s.",
                                unicode(instance), unicode(request.user))
                    continue
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


class TemplateAclUpdateView(AclUpdateView):
    model = InstanceTemplate

    def post(self, request, *args, **kwargs):
        template = self.get_object()
        if not (template.has_level(request.user, "owner") or
                getattr(template, 'owner', None) == request.user):
            logger.warning('Tried to set permissions of %s by non-owner %s.',
                           unicode(template), unicode(request.user))
            raise PermissionDenied()

        name = request.POST['perm-new-name']
        if (User.objects.filter(username=name).count() +
                Group.objects.filter(name=name).count() < 1
                and len(name) > 0):
            warning(request, _('User or group "%s" not found.') % name)
        else:
            self.set_levels(request, template)
            self.add_levels(request, template)

            post_for_disk = request.POST.copy()
            post_for_disk['perm-new'] = 'user'
            request.POST = post_for_disk
            for d in template.disks.all():
                self.add_levels(request, d)

        return redirect(reverse("dashboard.views.template-detail",
                                kwargs=self.kwargs))


class GroupAclUpdateView(AclUpdateView):
    model = Group

    def post(self, request, *args, **kwargs):
        instance = self.get_object().profile
        if not (instance.has_level(request.user, "owner") or
                getattr(instance, 'owner', None) == request.user):
            logger.warning('Tried to set permissions of %s by non-owner %s.',
                           unicode(instance), unicode(request.user))
            raise PermissionDenied()
        name = request.POST['perm-new-name']
        if (User.objects.filter(username=name).count() +
                Group.objects.filter(name=name).count() < 1
                and len(name) > 0):
            warning(request, _('User or group "%s" not found.') % name)
        else:
            self.set_levels(request, instance)
            self.add_levels(request, instance)
#        return redirect(self.profile)
        return redirect(reverse("dashboard.views.group-detail",
                                kwargs=self.kwargs))

    def repost(self, request, *args, **kwargs):
        group = self.get_object()
        if not (group.profile.has_level(request.user, "owner") or
                getattr(group.profile, 'owner', None) == request.user):
            logger.warning('Tried to set permissions of %s by non-owner %s.',
                           unicode(group), unicode(request.user))
            raise PermissionDenied()

        name = request.POST['perm-new-name']
        if (User.objects.filter(username=name).count() +
                Group.objects.filter(name=name).count() < 1
                and len(name) > 0):
            warning(request, _('User or group "%s" not found.') % name)
        else:
            self.set_levels(request, group.profile)
            self.add_levels(request, group.profile)

        return redirect(reverse("dashboard.views.group-detail",
                                kwargs=self.kwargs))


class TemplateCreate(SuccessMessageMixin, CreateView):
    model = InstanceTemplate
    form_class = TemplateForm
    template_name = "dashboard/template-create.html"
    success_message = _("Successfully created a new template!")

    def get(self, *args, **kwargs):
        if not self.request.user.has_perm('vm.create_template'):
            raise PermissionDenied()

        self.parent = self.request.GET.get("parent")
        return super(TemplateCreate, self).get(*args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(TemplateCreate, self).get_form_kwargs()
        kwargs['parent'] = getattr(self, "parent", None)
        kwargs['user'] = self.request.user
        return kwargs

    def post(self, request, *args, **kwargs):
        if not self.request.user.has_perm('vm.create_template'):
            raise PermissionDenied()

        form = self.form_class(request.POST, user=request.user)
        if not form.is_valid():
            return self.get(request, form, *args, **kwargs)
        post = form.cleaned_data
        for disk in post['disks']:
            if not disk.has_level(request.user, 'user'):
                raise PermissionDenied()

        return super(TemplateCreate, self).post(self, request, args, kwargs)

    def get_success_url(self):
        return reverse_lazy("dashboard.views.template-list")


class TemplateDetail(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = InstanceTemplate
    template_name = "dashboard/template-edit.html"
    form_class = TemplateForm
    success_message = _("Successfully modified template!")

    def get(self, request, *args, **kwargs):
        template = InstanceTemplate.objects.get(pk=kwargs['pk'])
        if not template.has_level(request.user, 'user'):
            raise PermissionDenied()
        if request.is_ajax():
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
            return super(TemplateDetail, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(TemplateDetail, self).get_context_data(**kwargs)
        context['acl'] = get_vm_acl_data(self.get_object())
        return context

    def get_success_url(self):
        return reverse_lazy("dashboard.views.template-detail",
                            kwargs=self.kwargs)

    def post(self, request, *args, **kwargs):
        template = self.get_object()
        if not template.has_level(request.user, 'owner'):
            raise PermissionDenied()
        for disk in self.get_object().disks.all():
            if not disk.has_level(request.user, 'user'):
                raise PermissionDenied()
        return super(TemplateDetail, self).post(self, request, args, kwargs)

    def get_form_kwargs(self):
        kwargs = super(TemplateDetail, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class TemplateList(LoginRequiredMixin, SingleTableView):
    template_name = "dashboard/template-list.html"
    model = InstanceTemplate
    table_class = TemplateListTable
    table_pagination = False

    def get_context_data(self, *args, **kwargs):
        context = super(TemplateList, self).get_context_data(*args, **kwargs)
        context['lease_table'] = LeaseListTable(Lease.objects.all())
        return context

    def get_queryset(self):
        logger.debug('TemplateList.get_queryset() called. User: %s',
                     unicode(self.request.user))
        return InstanceTemplate.get_objects_with_level(
            'user', self.request.user).all()


class TemplateDelete(LoginRequiredMixin, DeleteView):
    model = InstanceTemplate

    def get_success_url(self):
        return reverse("dashboard.views.template-list")

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/confirm/ajax-delete.html']
        else:
            return ['dashboard/confirm/base-delete.html']

    def delete(self, request, *args, **kwargs):
        object = self.get_object()
        if not object.has_level(request.user, 'owner'):
            raise PermissionDenied()

        object.delete()
        success_url = self.get_success_url()
        success_message = _("Template successfully deleted!")

        if request.is_ajax():
            return HttpResponse(
                json.dumps({'message': success_message}),
                content_type="application/json",
            )
        else:
            messages.success(request, success_message)
            return HttpResponseRedirect(success_url)


class VmList(LoginRequiredMixin, SingleTableView):
    template_name = "dashboard/vm-list.html"
    table_class = VmListTable
    table_pagination = False
    model = Instance

    def get(self, *args, **kwargs):
        if self.request.is_ajax():
            favs = Instance.objects.filter(
                favourite__user=self.request.user).values_list('pk', flat=True)
            instances = Instance.get_objects_with_level(
                'user', self.request.user).filter(
                destroyed=None).all()
            instances = [{
                'pk': i.pk,
                'name': i.name,
                'state': i.state,
                'fav': i.pk in favs} for i in instances]
            return HttpResponse(
                json.dumps(list(instances)),  # instances is ValuesQuerySet
                content_type="application/json",
            )
        else:
            return super(VmList, self).get(*args, **kwargs)

    def get_queryset(self):
        logger.debug('VmList.get_queryset() called. User: %s',
                     unicode(self.request.user))
        queryset = Instance.get_objects_with_level(
            'user', self.request.user).filter(destroyed=None)
        s = self.request.GET.get("s")
        if s:
            queryset = queryset.filter(name__icontains=s)
        return queryset


class NodeList(LoginRequiredMixin, SuperuserRequiredMixin, SingleTableView):
    template_name = "dashboard/node-list.html"
    model = Node
    table_class = NodeListTable
    table_pagination = False


class GroupList(LoginRequiredMixin, SuperuserRequiredMixin, SingleTableView):
    template_name = "dashboard/group-list.html"
    model = Group
    table_class = GroupListTable
    table_pagination = False


class GroupUserDelete(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):

    """This stuff deletes the group.
    """
    model = User
    template_name = "dashboard/confirm/base-delete.html"

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/confirm/ajax-delete.html']
        else:
            return ['dashboard/confirm/base-delete.html']

    def get_context_data(self, **kwargs):
        # this is redundant now, but if we wanna add more to print
        # we'll need this
        context = super(GroupUserDelete, self).get_context_data(**kwargs)
        return context

    # github.com/django/django/blob/master/django/views/generic/edit.py#L245
    def delete(self, request, *args, **kwargs):
        object = self.get_object()

        object.delete()
        success_url = self.get_success_url()
        success_message = _("Group successfully deleted!")

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


class GroupDelete(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):

    """This stuff deletes the group.
    """
    model = Group
    template_name = "dashboard/confirm/base-delete.html"

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/confirm/ajax-delete.html']
        else:
            return ['dashboard/confirm/base-delete.html']

    def get_context_data(self, **kwargs):
        # this is redundant now, but if we wanna add more to print
        # we'll need this
        context = super(GroupDelete, self).get_context_data(**kwargs)
        return context

    # github.com/django/django/blob/master/django/views/generic/edit.py#L245
    def delete(self, request, *args, **kwargs):
        object = self.get_object()

        object.delete()
        success_url = self.get_success_url()
        success_message = _("Group successfully deleted!")

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


class VmCreate(LoginRequiredMixin, TemplateView):

    form_class = VmCustomizeForm
    form = None

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/modal-wrapper.html']
        else:
            return ['dashboard/nojs-wrapper.html']

    def get(self, request, form=None, *args, **kwargs):
        form_error = form is not None
        template = (form.template.pk if form_error
                    else request.GET.get("template"))
        templates = InstanceTemplate.get_objects_with_level('user',
                                                            request.user)
        if form is None and template:
            form = self.form_class(user=request.user,
                                   template=templates.get(pk=template))

        context = self.get_context_data(**kwargs)
        if template:
            context.update({
                'template': 'dashboard/_vm-create-2.html',
                'box_title': _('Customize VM'),
                'ajax_title': False,
                'vm_create_form': form,
                'template_o': templates.get(pk=template),
            })
        else:
            context.update({
                'template': 'dashboard/_vm-create-1.html',
                'box_title': _('Create a VM'),
                'ajax_title': False,
                'templates': templates.all(),
            })
        return self.render_to_response(context)

    def __create_normal(self, request, *args, **kwargs):
        user = request.user
        template = InstanceTemplate.objects.get(
            pk=request.POST.get("template"))

        # permission check
        if not template.has_level(request.user, 'user'):
            raise PermissionDenied()

        inst = Instance.create_from_template(
            template=template, owner=user)
        return self.__deploy(request, inst)

    def __create_customized(self, request, *args, **kwargs):
        user = request.user
        form = self.form_class(
            request.POST, user=request.user,
            template=InstanceTemplate.objects.get(
                pk=request.POST.get("template")
            )
        )
        if not form.is_valid():
            return self.get(request, form, *args, **kwargs)
        post = form.cleaned_data

        template = InstanceTemplate.objects.get(pk=post['template'])
        # permission check
        if not template.has_level(user, 'user'):
            raise PermissionDenied()

        if request.user.has_perm('vm.set_resources'):
            ikwargs = {
                'name': post['name'],
                'num_cores': post['cpu_count'],
                'ram_size': post['ram_size'],
                'priority': post['cpu_priority'],
            }
            networks = [InterfaceTemplate(vlan=l, managed=l.managed)
                        for l in post['networks']]
            disks = post['disks']
            inst = Instance.create_from_template(
                template=template, owner=user, networks=networks,
                disks=disks, **ikwargs)
            return self.__deploy(request, inst)
        else:
            raise PermissionDenied()

    def __deploy(self, request, instance, *args, **kwargs):
        instance.deploy_async(user=request.user)
        messages.success(request, _('VM successfully created!'))
        path = instance.get_absolute_url()
        if request.is_ajax():
            return HttpResponse(json.dumps({'redirect': path}),
                                content_type="application/json")
        else:
            return redirect("%s#activity" % path)

    def post(self, request, *args, **kwargs):
        user = request.user

        # limit chekcs
        try:
            limit = user.profile.instance_limit
        except Exception as e:
            logger.debug('No profile or instance limit: %s', e)
        else:
            current = Instance.active.filter(owner=user).count()
            logger.debug('current use: %d, limit: %d', current, limit)
            if limit < current:
                messages.error(request,
                               _('Instance limit (%d) exceeded.') % limit)
                if request.is_ajax():
                    return HttpResponse(json.dumps({'redirect': '/'}),
                                        content_type="application/json")
                else:
                    return redirect('/')

        create_func = (self.__create_normal if
                       request.POST.get("customized") is None else
                       self.__create_customized)

        return create_func(request, *args, **kwargs)


class NodeCreate(LoginRequiredMixin, SuperuserRequiredMixin, TemplateView):

    form_class = HostForm
    hostform = None

    formset_class = inlineformset_factory(Host, Node, form=NodeForm, extra=1)
    formset = None

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/modal-wrapper.html']
        else:
            return ['dashboard/nojs-wrapper.html']

    def get(self, request, hostform=None, formset=None, *args, **kwargs):
        if hostform is None:
            hostform = self.form_class()
        if formset is None:
            formset = self.formset_class(instance=Host())
        context = self.get_context_data(**kwargs)
        context.update({
            'template': 'dashboard/node-create.html',
            'box_title': 'Create a Node',
            'hostform': hostform,
            'formset': formset,

        })
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super(NodeCreate, self).get_context_data(**kwargs)
        # TODO acl
        context.update({
        })

        return context

    # TODO handle not ajax posts
    def post(self, request, *args, **kwargs):
        if not self.request.user.is_authenticated():
            raise PermissionDenied()

        hostform = self.form_class(request.POST)
        formset = self.formset_class(request.POST, Host())
        if not hostform.is_valid():
            return self.get(request, hostform, formset, *args, **kwargs)
        hostform.setowner(request.user)
        savedform = hostform.save(commit=False)
        formset = self.formset_class(request.POST, instance=savedform)
        if not formset.is_valid():
            return self.get(request, hostform, formset, *args, **kwargs)

        savedform.save()
        nodemodel = formset.save()
        messages.success(request, _('Node successfully created!'))
        path = nodemodel[0].get_absolute_url()
        if request.is_ajax():
            return HttpResponse(json.dumps({'redirect': path}),
                                content_type="application/json")
        else:
            return redirect(path)


class VmDelete(LoginRequiredMixin, DeleteView):
    model = Instance
    template_name = "dashboard/confirm/base-delete.html"

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/confirm/ajax-delete.html']
        else:
            return ['dashboard/confirm/base-delete.html']

    def get_success_url(self):
        next = self.request.POST.get('next')
        if next:
            return next
        else:
            return reverse_lazy('dashboard.index')

    def get_context_data(self, **kwargs):
        object = self.get_object()
        if not object.has_level(self.request.user, 'owner'):
            raise PermissionDenied()
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


class NodeDelete(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):

    """This stuff deletes the node.
    """
    model = Node
    template_name = "dashboard/confirm/base-delete.html"

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/confirm/ajax-delete.html']
        else:
            return ['dashboard/confirm/base-delete.html']

    def get_context_data(self, **kwargs):
        # this is redundant now, but if we wanna add more to print
        # we'll need this
        context = super(NodeDelete, self).get_context_data(**kwargs)
        return context

    # github.com/django/django/blob/master/django/views/generic/edit.py#L245
    def delete(self, request, *args, **kwargs):
        object = self.get_object()

        object.delete()
        success_url = self.get_success_url()
        success_message = _("Node successfully deleted!")

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


class NodeStatus(LoginRequiredMixin, SuperuserRequiredMixin, DetailView):
    template_name = "dashboard/confirm/node-status.html"
    model = Node

    def get_success_url(self):
        next = self.request.GET.get('next')
        if next:
            return next
        else:
            return reverse_lazy("dashboard.views.node-detail",
                                kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super(NodeStatus, self).get_context_data(**kwargs)
        context['status'] = self.request.GET.get('status')
        return context

    def post(self, request, *args, **kwargs):
        if request.POST.get('new_status'):
            print self.request.GET.get('next')
            return self.__set_status(request)

    def __set_status(self, request):
        self.object = self.get_object()
        new_status = request.POST.get("new_status")

        if new_status == "enable":
            Node.objects.filter(pk=self.object.pk).update(
                **{'enabled': True})
        elif new_status == "disable":
            Node.objects.filter(pk=self.object.pk).update(
                **{'enabled': False})
        else:
            if request.is_ajax():
                return HttpResponse(content_type="application/json")

            else:
                return redirect(self.get_success_url())

        success_message = _("Node successfully changed status!")

        if request.is_ajax():
            response = {
                'message': success_message,
                'new_status': new_status,
                'node_pk': self.object.pk
            }
            return HttpResponse(
                json.dumps(response),
                content_type="application/json"
            )
        else:
            messages.success(request, success_message)
            return redirect(self.get_success_url())


class PortDelete(LoginRequiredMixin, DeleteView):
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


class VmMassDelete(LoginRequiredMixin, View):
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


class LeaseCreate(SuccessMessageMixin, CreateView):
    model = Lease
    form_class = LeaseForm
    template_name = "dashboard/lease-create.html"
    success_message = _("Successfully created a new lease!")

    def get_success_url(self):
        return reverse_lazy("dashboard.views.template-list")


class LeaseDetail(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Lease
    form_class = LeaseForm
    template_name = "dashboard/lease-edit.html"
    success_message = _("Successfully modified lease!")

    def get_success_url(self):
        return reverse_lazy("dashboard.views.lease-detail", kwargs=self.kwargs)


class LeaseDelete(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = Lease

    def get_success_url(self):
        return reverse("dashboard.views.template-list")

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/confirm/ajax-delete.html']
        else:
            return ['dashboard/confirm/base-delete.html']

    def delete(self, request, *args, **kwargs):
        object = self.get_object()

        object.delete()
        success_url = self.get_success_url()
        success_message = _("Lease successfully deleted!")

        if request.is_ajax():
            return HttpResponse(
                json.dumps({'message': success_message}),
                content_type="application/json",
            )
        else:
            messages.success(request, success_message)
            return HttpResponseRedirect(success_url)


@require_GET
def vm_activity(request, pk):
    instance = Instance.objects.get(pk=pk)
    if not instance.has_level(request.user, 'owner'):
        raise PermissionDenied()

    response = {}
    only_state = request.GET.get("only_state")

    response['state'] = instance.state
    if only_state is not None and only_state == "false":  # instance activity
        print "Sdsa"
        activities = render_to_string(
            "dashboard/vm-detail/_activity-timeline.html",
            {'activities': InstanceActivity.objects.filter(
                instance=instance, parent=None
            ).order_by('-started').select_related()}
        )
        response['activities'] = activities

    return HttpResponse(
        json.dumps(response),
        content_type="application/json"
    )


class FavouriteView(TemplateView):

    def post(self, *args, **kwargs):
        user = self.request.user
        vm = Instance.objects.get(pk=self.request.POST.get("vm"))
        try:
            Favourite.objects.get(instance=vm, user=user).delete()
            return HttpResponse("Deleted!")
        except Favourite.DoesNotExist:
            Favourite(instance=vm, user=user).save()
            return HttpResponse("Added!")


class TransferOwnershipView(LoginRequiredMixin, DetailView):
    model = Instance
    template_name = 'dashboard/vm-detail/tx-owner.html'

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


class GraphViewBase(LoginRequiredMixin, View):

    metrics = {
        'cpu': ('cactiStyle(alias(derivative(%s.cpu.usage),'
                '"cpu usage (%%)"))'),
        'memory': ('cactiStyle(alias(%s.memory.usage,'
                   '"memory usage (%%)"))'),
        'network': ('cactiStyle(aliasByMetric('
                    'derivative(%s.network.bytes_*)))'),
    }

    @staticmethod
    def get_graphite_url():
        graphite_host = getenv("GRAPHITE_HOST", None)
        graphite_port = getenv("GRAPHITE_PORT", None)

        if (graphite_host in ['', None] or graphite_port in ['', None]):
            logger.debug('GRAPHITE_HOST is empty.')
            return None

        return 'http://%s:%s' % (graphite_host, graphite_port)

    def get(self, request, pk, metric, time, *args, **kwargs):
        graphite_url = GraphViewBase.get_graphite_url()
        if graphite_url is None:
            raise Http404()

        if metric not in self.metrics.keys():
            raise SuspiciousOperation()

        try:
            instance = self.get_object(request, pk)
        except self.model.DoesNotExist:
            raise Http404()

        prefix = self.get_prefix(instance)
        target = self.metrics[metric] % prefix
        title = self.get_title(instance, metric)
        params = {'target': target,
                  'from': '-%s' % time,
                  'title': title.encode('UTF-8'),
                  'width': '500',
                  'height': '200'}
        response = requests.post('%s/render/' % graphite_url, data=params)
        return HttpResponse(response.content, mimetype="image/png")

    def get_prefix(self, instance):
        raise NotImplementedError("Subclass must implement abstract method")

    def get_title(self, instance, metric):
        raise NotImplementedError("Subclass must implement abstract method")

    def get_object(self, request, pk):
        instance = self.model.objects.get(id=pk)
        if not instance.has_level(request.user, 'user'):
            raise PermissionDenied()
        return instance


class VmGraphView(GraphViewBase):
    model = Instance

    def get_prefix(self, instance):
        return 'vm.%s' % instance.vm_name

    def get_title(self, instance, metric):
        return '%s (%s) - %s' % (instance.name, instance.vm_name, metric)
