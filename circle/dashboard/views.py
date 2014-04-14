from __future__ import unicode_literals

from os import getenv
import json
import logging
import re
from datetime import datetime
import requests

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.contrib.auth.views import login, redirect_to_login
from django.contrib.messages import warning
from django.core.exceptions import (
    PermissionDenied, SuspiciousOperation,
)
from django.core import signing
from django.core.urlresolvers import reverse, reverse_lazy
from django.db.models import Count
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.http import require_GET
from django.views.generic.detail import SingleObjectMixin
from django.views.generic import (TemplateView, DetailView, View, DeleteView,
                                  UpdateView, CreateView, ListView)
from django.contrib import messages
from django.utils.translation import ugettext as _
from django.template.defaultfilters import title as title_filter
from django.template.loader import render_to_string
from django.template import RequestContext

from django.forms.models import inlineformset_factory
from django_tables2 import SingleTableView
from braces.views import (
    LoginRequiredMixin, SuperuserRequiredMixin, AccessMixin
)

from .forms import (
    CircleAuthenticationForm, DiskAddForm, HostForm, LeaseForm, MyProfileForm,
    NodeForm, TemplateForm, TraitForm, VmCustomizeForm,
)
from .tables import (NodeListTable, NodeVmListTable,
                     TemplateListTable, LeaseListTable, GroupListTable,)
from vm.models import (
    Instance, instance_activity, InstanceActivity, InstanceTemplate, Interface,
    InterfaceTemplate, Lease, Node, NodeActivity, Trait,
)
from storage.models import Disk
from firewall.models import Vlan, Host, Rule
from dashboard.models import Favourite, Profile

logger = logging.getLogger(__name__)


def search_user(keyword):
    try:
        return User.objects.get(username=keyword)
    except User.DoesNotExist:
        try:
            return User.objects.get(profile__org_id=keyword)
        except User.DoesNotExist:
            return User.objects.get(email=keyword)


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
        user = self.request.user
        context = super(IndexView, self).get_context_data(**kwargs)

        # instances
        favs = Instance.objects.filter(favourite__user=self.request.user)
        instances = Instance.get_objects_with_level(
            'user', user).filter(destroyed_at=None)
        display = list(favs) + list(set(instances) - set(favs))
        for d in display:
            d.fav = True if d in favs else False
        context.update({
            'instances': display[:5],
            'more_instances': instances.count() - len(instances[:5])
        })

        running = instances.filter(status='RUNNING')
        stopped = instances.exclude(status__in=('RUNNING', 'NOSTATE'))

        context.update({
            'running_vms': running[:20],
            'running_vm_num': running.count(),
            'stopped_vm_num': stopped.count()
        })

        # nodes
        if user.is_superuser:
            nodes = Node.objects.all()
            context.update({
                'nodes': nodes[:5],
                'more_nodes': nodes.count() - len(nodes[:5]),
                'sum_node_num': nodes.count(),
                'node_num': {
                    'running': Node.get_state_count(True, True),
                    'missing': Node.get_state_count(False, True),
                    'disabled': Node.get_state_count(True, False),
                    'offline': Node.get_state_count(False, False)
                }
            })

        # groups
        groups = Group.objects.all()
        context.update({
            'groups': groups[:5],
            'more_groups': groups.count() - len(groups[:5]),
        })

        # template
        if user.has_perm('vm.create_template'):
            context['templates'] = InstanceTemplate.get_objects_with_level(
                'operator', user).all()[:5]

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


class VmDetailVncTokenView(CheckedDetailView):
    template_name = "dashboard/vm-detail.html"
    model = Instance

    def get(self, request, **kwargs):
        self.object = self.get_object()
        if not self.object.has_level(request.user, 'operator'):
            raise PermissionDenied()
        if self.object.node:
            with instance_activity(code_suffix='console-accessed',
                                   instance=self.object, user=request.user,
                                   concurrency_check=False):
                port = self.object.vnc_port
                host = str(self.object.node.host.ipv4)
                value = signing.dumps({'host': host, 'port': port},
                                      key=getenv("PROXY_SECRET", 'asdasd')),
                return HttpResponse('vnc/?d=%s' % value)
        else:
            raise Http404()


class VmDetailView(CheckedDetailView):
    template_name = "dashboard/vm-detail.html"
    model = Instance

    def get_context_data(self, **kwargs):
        context = super(VmDetailView, self).get_context_data(**kwargs)
        instance = context['instance']
        context.update({
            'graphite_enabled': VmGraphView.get_graphite_url() is not None,
            'vnc_url': reverse_lazy("dashboard.views.detail-vnc",
                                    kwargs={'pk': self.object.pk})
        })

        # activity data
        context['activities'] = (
            InstanceActivity.objects.filter(
                instance=self.object, parent=None).
            order_by('-started').
            select_related('user').prefetch_related('children'))

        context['vlans'] = Vlan.get_objects_with_level(
            'user', self.request.user
        ).exclude(
            pk__in=Interface.objects.filter(
                instance=self.get_object()).values_list("vlan", flat=True)
        ).all()
        context['acl'] = get_vm_acl_data(instance)
        context['forms'] = {
            'disk_add_form': DiskAddForm(
                user=self.request.user,
                is_template=False, object_pk=self.get_object().pk,
                prefix="disk"),
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
            'shut_down': self.__shut_down,
            'sleep': self.__sleep,
            'wake_up': self.__wake_up,
            'deploy': self.__deploy,
            'reset': self.__reset,
            'reboot': self.__reboot,
            'shut_off': self.__shut_off,
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
            'max_ram_size': request.POST.get('ram-size'),  # TODO: max_ram
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
        else:
            return redirect(reverse_lazy("dashboard.views.detail",
                            kwargs={'pk': self.object.pk}))

    def __add_port(self, request):
        object = self.get_object()
        if (not object.has_level(request.user, 'owner') or
                not request.user.has_perm('vm.config_ports')):
            raise PermissionDenied()

        port = request.POST.get("port")
        proto = request.POST.get("proto")

        try:
            error = None
            interfaces = object.interface_set.all()
            host = Host.objects.get(pk=request.POST.get("host_pk"),
                                    interface__in=interfaces)
            host.add_port(proto, private=port)
        except Host.DoesNotExist:
            logger.error('Tried to add port to nonexistent host %d. User: %s. '
                         'Instance: %s', request.POST.get("host_pk"),
                         unicode(request.user), object)
            raise PermissionDenied()
        except ValueError:
            error = _("There is a problem with your input!")
        except Exception as e:
            error = _("Unknown error.")
            logger.error(e)

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

        vlan = get_object_or_404(Vlan, pk=request.POST.get("new_network_vlan"))
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
        self.object.save_as_template.async(name=new_name,
                                           user=request.user)
        messages.success(request, _("Saving instance as template!"))
        return redirect("%s#activity" % self.object.get_absolute_url())

    def __shut_down(self, request):
        self.object = self.get_object()
        if not self.object.has_level(request.user, 'owner'):
            raise PermissionDenied()

        self.object.shutdown.async(user=request.user)
        return redirect("%s#activity" % self.object.get_absolute_url())

    def __sleep(self, request):
        self.object = self.get_object()
        if not self.object.has_level(request.user, 'owner'):
            raise PermissionDenied()

        self.object.sleep.async(user=request.user)
        return redirect("%s#activity" % self.object.get_absolute_url())

    def __wake_up(self, request):
        self.object = self.get_object()
        if not self.object.has_level(request.user, 'owner'):
            raise PermissionDenied()

        self.object.wake_up.async(user=request.user)
        return redirect("%s#activity" % self.object.get_absolute_url())

    def __deploy(self, request):
        self.object = self.get_object()
        if not self.object.has_level(request.user, 'owner'):
            raise PermissionDenied()

        self.object.deploy.async(user=request.user)
        return redirect("%s#activity" % self.object.get_absolute_url())

    def __reset(self, request):
        self.object = self.get_object()
        if not self.object.has_level(request.user, 'owner'):
            raise PermissionDenied()

        self.object.reset.async(user=request.user)
        return redirect("%s#activity" % self.object.get_absolute_url())

    def __reboot(self, request):
        self.object = self.get_object()
        if not self.object.has_level(request.user, 'owner'):
            raise PermissionDenied()

        self.object.reboot.async(user=request.user)
        return redirect("%s#activity" % self.object.get_absolute_url())

    def __shut_off(self, request):
        self.object = self.get_object()
        if not self.object.has_level(request.user, 'owner'):
            raise PermissionDenied()

        self.object.shut_off.async(user=request.user)
        return redirect("%s#activity" % self.object.get_absolute_url())


class NodeDetailView(LoginRequiredMixin, SuperuserRequiredMixin, DetailView):
    template_name = "dashboard/node-detail.html"
    model = Node
    form = None
    form_class = TraitForm

    def get_context_data(self, form=None, **kwargs):
        if form is None:
            form = self.form_class()
        context = super(NodeDetailView, self).get_context_data(**kwargs)
        instances = Instance.active.filter(node=self.object)
        context['table'] = NodeVmListTable(instances)
        na = NodeActivity.objects.filter(
            node=self.object, parent=None
        ).order_by('-started').select_related()
        context['activities'] = na
        context['trait_form'] = form
        context['graphite_enabled'] = (
            NodeGraphView.get_graphite_url() is not None)
        return context

    def post(self, request, *args, **kwargs):
        if request.POST.get('new_name'):
            return self.__set_name(request)
        if request.POST.get('to_remove'):
            return self.__remove_trait(request)
        return redirect(reverse_lazy("dashboard.views.node-detail",
                                     kwargs={'pk': self.get_object().pk}))

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

    def __remove_trait(self, request):
        try:
            to_remove = request.POST.get('to_remove')
            self.object = self.get_object()
            self.object.traits.remove(to_remove)
            message = u"Success"
        except:  # note this won't really happen
            message = u"Not success"

        if request.is_ajax():
            return HttpResponse(
                json.dumps({'message': message}),
                content_type="application/json"
            )
        else:
            return redirect(self.object.get_absolute_url())


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
        else:
            post = form.cleaned_data

            networks = self.__create_networks(post.pop("networks"))
            req_traits = post.pop("req_traits")
            tags = post.pop("tags")
            post['pw'] = User.objects.make_random_password()
            post.pop("parent")
            post['max_ram_size'] = post['ram_size']
            inst = Instance.create(params=post, disks=[], networks=networks,
                                   tags=tags, req_traits=req_traits)
            messages.success(request, _("The template has been created, "
                                        "you can now add disks to it!"))
            return redirect("%s#resources" % inst.get_absolute_url())

        return super(TemplateCreate, self).post(self, request, args, kwargs)

    def __create_networks(self, vlans):
        networks = []
        for v in vlans:
            networks.append(InterfaceTemplate(vlan=v, managed=v.managed))
        return networks

    def get_success_url(self):
        return reverse_lazy("dashboard.views.template-list")


class TemplateDetail(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = InstanceTemplate
    template_name = "dashboard/template-edit.html"
    form_class = TemplateForm
    success_message = _("Successfully modified template!")

    def get(self, request, *args, **kwargs):
        template = self.get_object()
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
        obj = self.get_object()
        context = super(TemplateDetail, self).get_context_data(**kwargs)
        context['acl'] = get_vm_acl_data(obj)
        context['disks'] = obj.disks.all()
        context['disk_add_form'] = DiskAddForm(
            user=self.request.user,
            is_template=True,
            object_pk=obj.pk,
            prefix="disk",
        )
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


class VmList(LoginRequiredMixin, ListView):
    template_name = "dashboard/vm-list.html"

    def get(self, *args, **kwargs):
        if self.request.is_ajax():
            favs = Instance.objects.filter(
                favourite__user=self.request.user).values_list('pk', flat=True)
            instances = Instance.get_objects_with_level(
                'user', self.request.user).filter(
                destroyed_at=None).all()
            instances = [{
                'pk': i.pk,
                'name': i.name,
                'icon': i.get_status_icon(),
                'host': "" if not i.primary_host else i.primary_host.hostname,
                'status': i.get_status_display(),
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
            'user', self.request.user).filter(destroyed_at=None)
        s = self.request.GET.get("s")
        if s:
            queryset = queryset.filter(name__icontains=s)
        return queryset.select_related('owner', 'node')


class NodeList(LoginRequiredMixin, SuperuserRequiredMixin, SingleTableView):
    template_name = "dashboard/node-list.html"
    table_class = NodeListTable
    table_pagination = False

    def get_queryset(self):
        return Node.objects.annotate(
            number_of_VMs=Count('instance_set')).select_related('host')


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

        instances = [Instance.create_from_template(
            template=template, owner=user)]
        return self.__deploy(request, instances)

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

            ikwargs.update({
                'template': template,
                'owner': user,
                'networks': networks,
                'disks': disks,
            })

            amount = post['amount']
            instances = Instance.mass_create_from_template(amount=amount,
                                                           **ikwargs)
            return self.__deploy(request, instances)
        else:
            raise PermissionDenied()

    def __deploy(self, request, instances, *args, **kwargs):
        for i in instances:
            i.deploy.async(user=request.user)

        if len(instances) > 1:
            messages.success(request, _("Successfully created %d VMs!" %
                                        len(instances)))
            path = reverse("dashboard.index")
        else:
            messages.success(request, _("VM successfully created!"))
            path = instances[0].get_absolute_url()

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

        object.destroy.async(user=request.user)
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


class NodeAddTraitView(SuperuserRequiredMixin, DetailView):
    model = Node
    template_name = "dashboard/node-add-trait.html"

    def get_success_url(self):
        next = self.request.GET.get('next')
        if next:
            return next
        else:
            return self.object.get_absolute_url()

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = super(NodeAddTraitView, self).get_context_data(**kwargs)
        context['form'] = (TraitForm(self.request.POST) if self.request.POST
                           else TraitForm())
        return context

    def post(self, request, pk, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = context['form']
        if form.is_valid():
            node = self.object
            n = form.cleaned_data['name']
            trait, created = Trait.objects.get_or_create(name=n)
            node.traits.add(trait)
            success_message = _("Trait successfully added to node.")
            messages.success(request, success_message)
            return redirect(self.get_success_url())
        else:
            return self.get(self, request, pk, *args, **kwargs)


class NodeStatus(LoginRequiredMixin, SuperuserRequiredMixin, DetailView):
    template_name = "dashboard/confirm/node-status.html"
    model = Node

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/confirm/ajax-node-status.html']
        else:
            return ['dashboard/confirm/node-status.html']

    def get_success_url(self):
        next = self.request.GET.get('next')
        if next:
            return next
        else:
            return reverse_lazy("dashboard.views.node-detail",
                                kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super(NodeStatus, self).get_context_data(**kwargs)
        if self.object.enabled:
            context['status'] = "disable"
        else:
            context['status'] = "enable"
        return context

    def post(self, request, *args, **kwargs):
        if request.POST.get('change_status') is not None:
            return self.__set_status(request)
        return redirect(reverse_lazy("dashboard.views.node-detail",
                                     kwargs={'pk': self.get_object().pk}))

    def __set_status(self, request):
        self.object = self.get_object()
        if not self.object.enabled:
            self.object.enable(user=request.user)
        else:
            self.object.disable(user=request.user)
        success_message = _("Node successfully changed status!")

        if request.is_ajax():
            response = {
                'message': success_message,
                'node_pk': self.object.pk
            }
            return HttpResponse(
                json.dumps(response),
                content_type="application/json"
            )
        else:
            messages.success(request, success_message)
            return redirect(self.get_success_url())


class NodeFlushView(LoginRequiredMixin, SuperuserRequiredMixin, DetailView):
    template_name = "dashboard/confirm/node-flush.html"
    model = Node

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/confirm/ajax-node-flush.html']
        else:
            return ['dashboard/confirm/node-flush.html']

    def get_success_url(self):
        next = self.request.GET.get('next')
        if next:
            return next
        else:
            return reverse_lazy("dashboard.views.node-detail",
                                kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super(NodeFlushView, self).get_context_data(**kwargs)
        return context

    def post(self, request, *args, **kwargs):
        if request.POST.get('flush') is not None:
            return self.__flush(request)
        return redirect(reverse_lazy("dashboard.views.node-detail",
                                     kwargs={'pk': self.get_object().pk}))

    def __flush(self, request):
        self.object = self.get_object()
        self.object.flush.async(user=request.user)
        success_message = _("Node successfully flushed!")
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
                i.destroy.async(user=request.user)
                names.append(i.name)

        success_message = _("Mass delete complete, the following VMs were "
                            "deleted: %s!") % u', '.join(names)

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


class LeaseCreate(LoginRequiredMixin, SuperuserRequiredMixin,
                  SuccessMessageMixin, CreateView):
    model = Lease
    form_class = LeaseForm
    template_name = "dashboard/lease-create.html"
    success_message = _("Successfully created a new lease!")

    def get_success_url(self):
        return reverse_lazy("dashboard.views.template-list")


class LeaseDetail(LoginRequiredMixin, SuperuserRequiredMixin,
                  SuccessMessageMixin, UpdateView):
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
    only_status = request.GET.get("only_status")

    response['human_readable_status'] = instance.get_status_display()
    response['status'] = instance.status
    response['icon'] = instance.get_status_icon()
    if only_status == "false":  # instance activity
        context = {
            'activities': InstanceActivity.objects.filter(
                instance=instance, parent=None
            ).order_by('-started').select_related()
        }

        activities = render_to_string(
            "dashboard/vm-detail/_activity-timeline.html",
            RequestContext(request, context),
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
            new_owner = search_user(request.POST['name'])
        except User.DoesNotExist:
            messages.error(request, _('Can not find specified user.'))
            return self.get(request, *args, **kwargs)
        except KeyError:
            raise SuspiciousOperation()

        obj = self.get_object()
        if not (obj.owner == request.user or
                request.user.is_superuser):
            raise PermissionDenied()

        token = signing.dumps((obj.pk, new_owner.pk),
                              salt=TransferOwnershipConfirmView.get_salt())
        token_path = reverse(
            'dashboard.views.vm-transfer-ownership-confirm', args=[token])
        try:
            new_owner.profile.notify(
                _('Ownership offer'),
                'dashboard/notifications/ownership-offer.html',
                {'instance': obj, 'token': token_path})
        except Profile.DoesNotExist:
            messages.error(request, _('Can not notify selected user.'))
        else:
            messages.success(request,
                             _('User %s is notified about the offer.') % (
                                 unicode(new_owner), ))

        return redirect(reverse_lazy("dashboard.views.detail",
                                     kwargs={'pk': obj.pk}))


class AbstractVmFunctionView(AccessMixin, View):
    """Abstract instance-action view.

    User can do the action with a valid token or if has at least required_level
    ACL level for the instance.

    Children should at least implement/add template_name, success_message,
    url_name, and do_action().
    """
    token_max_age = 3 * 24 * 3600
    required_level = 'owner'
    success_message = _("Failed to perform requested action.")

    @classmethod
    def check_acl(cls, instance, user):
        if not instance.has_level(user, cls.required_level):
            raise PermissionDenied()

    @classmethod
    def get_salt(cls):
        return unicode(cls)

    @classmethod
    def get_token(cls, instance, user, *args):
        t = tuple([getattr(i, 'pk', i) for i in [instance, user] + list(args)])
        return signing.dumps(t, salt=cls.get_salt())

    @classmethod
    def get_token_url(cls, instance, user, *args):
        key = cls.get_token(instance, user, *args)
        args = (instance.pk, key) + args
        return reverse(cls.url_name, args=args)
        # this wont work, CBVs suck: reverse(cls.as_view(), args=args)

    def get_template_names(self):
        return [self.template_name]

    def get(self, request, pk, key=None, *args, **kwargs):
        class LoginNeeded(Exception):
            pass
        pk = int(pk)
        instance = get_object_or_404(Instance, pk=pk)
        try:
            if key:
                logger.debug('Confirm dialog for token %s.', key)
                try:
                    self.validate_key(pk, key)
                except signing.SignatureExpired:
                    messages.error(request, _(
                        'The token has expired, please log in.'))
                    raise LoginNeeded()
                self.key = key
            else:
                if not request.user.is_authenticated():
                    raise LoginNeeded()
                self.check_acl(instance, request.user)
        except LoginNeeded:
            return redirect_to_login(request.get_full_path(),
                                     self.get_login_url(),
                                     self.get_redirect_field_name())
        except SuspiciousOperation as e:
            messages.error(request, _('This token is invalid.'))
            logger.warning('This token %s is invalid. %s', key, unicode(e))
            raise PermissionDenied()
        return render(request, self.get_template_names(),
                      self.get_context(instance))

    def post(self, request, pk, key=None, *args, **kwargs):
        class LoginNeeded(Exception):
            pass
        pk = int(pk)
        instance = get_object_or_404(Instance, pk=pk)

        try:
            if not request.user.is_authenticated() and key:
                try:
                    user = self.validate_key(pk, key)
                except signing.SignatureExpired:
                    messages.error(request, _(
                        'The token has expired, please log in.'))
                    raise LoginNeeded()
                self.key = key
            else:
                user = request.user
                self.check_acl(instance, request.user)
        except LoginNeeded:
            return redirect_to_login(request.get_full_path(),
                                     self.get_login_url(),
                                     self.get_redirect_field_name())
        except SuspiciousOperation as e:
            messages.error(request, _('This token is invalid.'))
            logger.warning('This token %s is invalid. %s', key, unicode(e))
            raise PermissionDenied()

        if self.do_action(instance, user):
            messages.success(request, self.success_message)
        else:
            messages.error(request, self.fail_message)
        return HttpResponseRedirect(instance.get_absolute_url())

    def validate_key(self, pk, key):
        """Get object based on signed token.
        """
        try:
            data = signing.loads(key, salt=self.get_salt())
            logger.debug('Token data: %s', unicode(data))
            instance, user = data
            logger.debug('Extracted token data: instance: %s, user: %s',
                         unicode(instance), unicode(user))
        except (signing.BadSignature, ValueError, TypeError) as e:
            logger.warning('Tried invalid token. Token: %s, user: %s. %s',
                           key, unicode(self.request.user), unicode(e))
            raise SuspiciousOperation()

        try:
            instance, user = signing.loads(key, max_age=self.token_max_age,
                                           salt=self.get_salt())
            logger.debug('Extracted non-expired token data: %s, %s',
                         unicode(instance), unicode(user))
        except signing.BadSignature as e:
            raise signing.SignatureExpired()

        if pk != instance:
            logger.debug('pk (%d) != instance (%d)', pk, instance)
            raise SuspiciousOperation()
        user = User.objects.get(pk=user)
        return user

    def do_action(self, instance, user):  # noqa
        raise NotImplementedError('Please override do_action(instance, user)')

    def get_context(self, instance):
        context = {'instance': instance}
        if getattr(self, 'key', None) is not None:
            context['key'] = self.key
        return context


class VmRenewView(AbstractVmFunctionView):
    """User can renew an instance."""
    template_name = 'dashboard/confirm/base-renew.html'
    success_message = _("Virtual machine is successfully renewed.")
    url_name = 'dashboard.views.vm-renew'

    def get_context(self, instance):
        context = super(VmRenewView, self).get_context(instance)
        (context['time_of_suspend'],
         context['time_of_delete']) = instance.get_renew_times()
        return context

    def do_action(self, instance, user):
        instance.renew(user=user)
        logger.info('Instance %s renewed by %s.', unicode(instance),
                    unicode(user))
        return True


class TransferOwnershipConfirmView(LoginRequiredMixin, View):
    """User can accept an ownership offer."""

    max_age = 3 * 24 * 3600
    success_message = _("Ownership successfully transferred to you.")

    @classmethod
    def get_salt(cls):
        return unicode(cls)

    def get(self, request, key, *args, **kwargs):
        """Confirm ownership transfer based on token.
        """
        logger.debug('Confirm dialog for token %s.', key)
        try:
            instance, new_owner = self.get_instance(key, request.user)
        except PermissionDenied:
            messages.error(request, _('This token is for an other user.'))
            raise
        except SuspiciousOperation:
            messages.error(request, _('This token is invalid or has expired.'))
            raise PermissionDenied()
        return render(request,
                      "dashboard/confirm/base-transfer-ownership.html",
                      dictionary={'instance': instance, 'key': key})

    def post(self, request, key, *args, **kwargs):
        """Really transfer ownership based on token.
        """
        instance, owner = self.get_instance(key, request.user)

        old = instance.owner
        with instance_activity(code_suffix='ownership-transferred',
                               instance=instance, user=request.user):
            instance.owner = request.user
            instance.clean()
            instance.save()
        messages.success(request, self.success_message)
        logger.info('Ownership of %s transferred from %s to %s.',
                    unicode(instance), unicode(old), unicode(request.user))
        if old.profile:
            old.profile.notify(
                _('Ownership accepted'),
                'dashboard/notifications/ownership-accepted.html',
                {'instance': instance})
        return HttpResponseRedirect(instance.get_absolute_url())

    def get_instance(self, key, user):
        """Get object based on signed token.
        """
        try:
            instance, new_owner = (
                signing.loads(key, max_age=self.max_age,
                              salt=self.get_salt()))
        except (signing.BadSignature, ValueError, TypeError) as e:
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
        target = self.metrics[metric] % {'prefix': prefix}
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
    metrics = {
        'cpu': ('cactiStyle(alias(nonNegativeDerivative(%(prefix)s.cpu.usage),'
                '"cpu usage (%%)"))'),
        'memory': ('cactiStyle(alias(%(prefix)s.memory.usage,'
                   '"memory usage (%%)"))'),
        'network': (
            'group('
            'aliasSub(nonNegativeDerivative(%(prefix)s.network.bytes_recv*),'
            ' ".*-(\d+)\\)", "out (vlan \\1)"),'
            'aliasSub(nonNegativeDerivative(%(prefix)s.network.bytes_sent*),'
            ' ".*-(\d+)\\)", "in (vlan \\1)"))'),
    }
    model = Instance

    def get_prefix(self, instance):
        return 'vm.%s' % instance.vm_name

    def get_title(self, instance, metric):
        return '%s (%s) - %s' % (instance.name, instance.vm_name, metric)


class NodeGraphView(SuperuserRequiredMixin, GraphViewBase):
    metrics = {
        'cpu': ('cactiStyle(alias(nonNegativeDerivative(%(prefix)s.cpu.times),'
                '"cpu usage (%%)"))'),
        'memory': ('cactiStyle(alias(%(prefix)s.memory.usage,'
                   '"memory usage (%%)"))'),
        'network': ('cactiStyle(aliasByMetric('
                    'nonNegativeDerivative(%(prefix)s.network.bytes_*)))'),
    }
    model = Node

    def get_prefix(self, instance):
        return 'circle.%s' % instance.name

    def get_title(self, instance, metric):
        return '%s - %s' % (instance.name, metric)

    def get_object(self, request, pk):
        return self.model.objects.get(id=pk)


class NotificationView(LoginRequiredMixin, TemplateView):

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/_notifications-timeline.html']
        else:
            return ['dashboard/notifications.html']

    def get_context_data(self, *args, **kwargs):
        context = super(NotificationView, self).get_context_data(
            *args, **kwargs)
        # we need to convert it to list, otherwise it's gonna be
        # similar to a QuerySet and update everything to
        # read status after get
        n = 10 if self.request.is_ajax() else 1000
        context['notifications'] = list(
            self.request.user.notification_set.values()[:n])
        return context

    def get(self, *args, **kwargs):
        response = super(NotificationView, self).get(*args, **kwargs)
        un = self.request.user.notification_set.filter(status="new")
        for u in un:
            u.status = "read"
            u.save()
        return response


class VmMigrateView(SuperuserRequiredMixin, TemplateView):

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/modal-wrapper.html']
        else:
            return ['dashboard/nojs-wrapper.html']

    def get(self, request, form=None, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        vm = Instance.objects.get(pk=kwargs['pk'])
        context.update({
            'template': 'dashboard/_vm-migrate.html',
            'box_title': _('Migrate %(name)s' % {'name': vm.name}),
            'ajax_title': True,
            'vm': vm,
            'nodes': [n for n in Node.objects.filter(enabled=True)
                      if n.state == "ONLINE"]
        })
        return self.render_to_response(context)

    def post(self, *args, **kwargs):
        node = self.request.POST.get("node")
        vm = Instance.objects.get(pk=kwargs['pk'])

        if node:
            node = Node.objects.get(pk=node)
            vm.migrate.async(to_node=node, user=self.request.user)
        else:
            messages.error(self.request, _("You didn't select a node!"))

        return redirect("%s#activity" % vm.get_absolute_url())


def circle_login(request):
    authentication_form = CircleAuthenticationForm
    extra_context = {
        'saml2': hasattr(settings, "SAML_CONFIG")
    }
    response = login(request, authentication_form=authentication_form,
                     extra_context=extra_context)
    set_language_cookie(request, response)
    return response


class DiskAddView(TemplateView):

    def post(self, *args, **kwargs):
        is_template = self.request.POST.get("disk-is_template")
        object_pk = self.request.POST.get("disk-object_pk")
        is_template = int(is_template) == 1
        if is_template:
            obj = InstanceTemplate.objects.get(pk=object_pk)
        else:
            obj = Instance.objects.get(pk=object_pk)

        if not obj.has_level(self.request.user, 'owner'):
            raise PermissionDenied()

        form = DiskAddForm(
            self.request.POST,
            user=self.request.user,
            is_template=is_template, object_pk=object_pk,
            prefix="disk"
        )

        if form.is_valid():
            if form.cleaned_data.get("size"):
                messages.success(self.request, _("Disk successfully added!"))
            else:
                messages.success(self.request, _("Disk download started!"))
            form.save()
        else:
            error = "<br /> ".join(["<strong>%s</strong>: %s" %
                                    (title_filter(i[0]), i[1][0])
                                    for i in form.errors.items()])
            messages.error(self.request, error)

        if is_template:
            r = obj.get_absolute_url()
        else:
            r = obj.get_absolute_url()
            r = "%s#resources" % r
        return redirect(r)


class MyPreferencesView(UpdateView):

    model = Profile
    form_class = MyProfileForm

    def get_object(self, queryset=None):
        if self.request.user.is_anonymous():
            raise PermissionDenied()
        try:
            return self.request.user.profile
        except Profile.DoesNotExist:
            raise Http404(_("You don't have a profile."))

    def form_valid(self, form):
        response = super(MyPreferencesView, self).form_valid(form)
        set_language_cookie(self.request, response)
        return response


def set_language_cookie(request, response, lang=None):
    if lang is None:
        try:
            lang = request.user.profile.preferred_language
        except:
            return

    cname = getattr(settings, 'LANGUAGE_COOKIE_NAME', 'django_language')
    response.set_cookie(cname, lang, 365 * 86400)


class DiskRemoveView(DeleteView):
    model = Disk

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/confirm/ajax-delete.html']
        else:
            return ['dashboard/confirm/base-delete.html']

    def get_context_data(self, **kwargs):
        context = super(DiskRemoveView, self).get_context_data(**kwargs)
        disk = self.get_object()
        app = disk.get_appliance()
        context['title'] = _("Disk remove confirmation")
        context['text'] = _("Are you sure you want to remove "
                            "<strong>%(disk)s</strong> from "
                            "<strong>%(app)s</strong>?" % {'disk': disk,
                                                           'app': app}
                            )
        return context

    def delete(self, request, *args, **kwargs):
        disk = self.get_object()
        if not disk.has_level(request.user, 'owner'):
            raise PermissionDenied()

        disk = self.get_object()
        app = disk.get_appliance()

        app.disks.remove(disk)
        disk.destroy()

        next_url = request.POST.get("next")
        success_url = next_url if next_url else app.get_absolute_url()
        success_message = _("Disk successfully removed!")

        if request.is_ajax():
            return HttpResponse(
                json.dumps({'message': success_message}),
                content_type="application/json",
            )
        else:
            messages.success(request, success_message)
            return HttpResponseRedirect("%s#resources" % success_url)


@require_GET
def get_disk_download_status(request, pk):
    disk = Disk.objects.get(pk=pk)
    if not disk.has_level(request.user, 'owner'):
        raise PermissionDenied()

    return HttpResponse(
        json.dumps({
            'percentage': disk.get_download_percentage(),
            'failed': disk.failed
        }),
        content_type="application/json",
    )


class InstanceActivityDetail(SuperuserRequiredMixin, DetailView):
    model = InstanceActivity
    template_name = 'dashboard/instanceactivity_detail.html'

    def get_context_data(self, **kwargs):
        ctx = super(InstanceActivityDetail, self).get_context_data(**kwargs)
        ctx['activities'] = (
            self.object.instance.activity_log.filter(parent=None).
            order_by('-started').select_related('user').
            prefetch_related('children'))
        return ctx
