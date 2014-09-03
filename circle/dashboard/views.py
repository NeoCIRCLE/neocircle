# Copyright 2014 Budapest University of Technology and Economics (BME IK)
#
# This file is part of CIRCLE Cloud.
#
# CIRCLE is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# CIRCLE is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along
# with CIRCLE.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals, absolute_import

from collections import OrderedDict
from itertools import chain
from os import getenv
from os.path import join, normpath, dirname, basename
from urlparse import urljoin
import json
import logging
import re
import requests

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.contrib.auth.views import login, redirect_to_login
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import (
    PermissionDenied, SuspiciousOperation,
)
from django.core.cache import get_cache
from django.core import signing
from django.core.urlresolvers import reverse, reverse_lazy
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import (
    redirect, render, get_object_or_404, render_to_response,
)
from django.views.decorators.http import require_GET, require_POST
from django.views.generic.detail import SingleObjectMixin
from django.views.generic import (TemplateView, DetailView, View, DeleteView,
                                  UpdateView, CreateView, ListView)
from django.contrib import messages
from django.utils.translation import (
    ugettext as _, ugettext_noop, ungettext_lazy
)
from django.template.loader import render_to_string
from django.template import RequestContext

from django.forms.models import inlineformset_factory
from django_tables2 import SingleTableView
from braces.views import (LoginRequiredMixin, SuperuserRequiredMixin,
                          PermissionRequiredMixin)
from braces.views._access import AccessMixin
from celery.exceptions import TimeoutError

from django_sshkey.models import UserKey

from .forms import (
    CircleAuthenticationForm, HostForm, LeaseForm, MyProfileForm,
    NodeForm, TemplateForm, TraitForm, VmCustomizeForm, GroupCreateForm,
    UserCreationForm, GroupProfileUpdateForm, UnsubscribeForm,
    VmSaveForm, UserKeyForm, VmRenewForm, VmStateChangeForm,
    CirclePasswordChangeForm, VmCreateDiskForm, VmDownloadDiskForm,
    TraitsForm, RawDataForm, GroupPermissionForm, AclUserAddForm,
    VmResourcesForm, VmAddInterfaceForm, VmListSearchForm, ConnectCommandForm
)

from .tables import (
    NodeListTable, TemplateListTable, LeaseListTable,
    GroupListTable, UserKeyListTable, ConnectCommandListTable,
)
from common.models import (
    HumanReadableObject, HumanReadableException, fetch_human_exception,
    create_readable,
)
from vm.models import (
    Instance, instance_activity, InstanceActivity, InstanceTemplate, Interface,
    InterfaceTemplate, Lease, Node, NodeActivity, Trait,
)
from storage.models import Disk
from firewall.models import Vlan, Host, Rule
from .models import (Favourite, Profile, GroupProfile, FutureMember,
                     ConnectCommand)

from .store_api import Store, NoStoreException, NotOkException

logger = logging.getLogger(__name__)
saml_available = hasattr(settings, "SAML_CONFIG")


def search_user(keyword):
    try:
        return User.objects.get(username=keyword)
    except User.DoesNotExist:
        try:
            return User.objects.get(profile__org_id=keyword)
        except User.DoesNotExist:
            return User.objects.get(email=keyword)


class RedirectToLoginMixin(AccessMixin):

    redirect_exception_classes = (PermissionDenied, )

    def dispatch(self, request, *args, **kwargs):
        try:
            return super(RedirectToLoginMixin, self).dispatch(
                request, *args, **kwargs)
        except self.redirect_exception_classes:
            if not request.user.is_authenticated():
                return redirect_to_login(request.get_full_path(),
                                         self.get_login_url(),
                                         self.get_redirect_field_name())
            else:
                raise


class GroupCodeMixin(object):

    @classmethod
    def get_available_group_codes(cls, request):
        newgroups = []
        if saml_available:
            from djangosaml2.cache import StateCache, IdentityCache
            from djangosaml2.conf import get_config
            from djangosaml2.views import _get_subject_id
            from saml2.client import Saml2Client

            state = StateCache(request.session)
            conf = get_config(None, request)
            client = Saml2Client(conf, state_cache=state,
                                 identity_cache=IdentityCache(request.session),
                                 logger=logger)
            subject_id = _get_subject_id(request.session)
            identity = client.users.get_identity(subject_id,
                                                 check_not_on_or_after=False)
            if identity:
                attributes = identity[0]
                owneratrs = getattr(
                    settings, 'SAML_GROUP_OWNER_ATTRIBUTES', [])
                for group in chain(*[attributes[i]
                                     for i in owneratrs if i in attributes]):
                    try:
                        GroupProfile.search(group)
                    except Group.DoesNotExist:
                        newgroups.append(group)

        return newgroups


class FilterMixin(object):

    def get_queryset_filters(self):
        filters = {}
        for item in self.allowed_filters:
            if item in self.request.GET:
                filters[self.allowed_filters[item]] = (
                    self.request.GET[item].split(",")
                    if self.allowed_filters[item].endswith("__in") else
                    self.request.GET[item])

        return filters

    def get_queryset(self):
        return super(FilterMixin,
                     self).get_queryset().filter(**self.get_queryset_filters())


class IndexView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        user = self.request.user
        context = super(IndexView, self).get_context_data(**kwargs)

        # instances
        favs = Instance.objects.filter(favourite__user=self.request.user)
        instances = Instance.get_objects_with_level(
            'user', user, disregard_superuser=True).filter(destroyed_at=None)
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
        if user.has_module_perms('auth'):
            profiles = GroupProfile.get_objects_with_level('operator', user)
            groups = Group.objects.filter(groupprofile__in=profiles)
            context.update({
                'groups': groups[:5],
                'more_groups': groups.count() - len(groups[:5]),
            })

        # template
        if user.has_perm('vm.create_template'):
            context['templates'] = InstanceTemplate.get_objects_with_level(
                'operator', user, disregard_superuser=True).all()[:5]

        # toplist
        if settings.STORE_URL:
            cache_key = "files-%d" % self.request.user.pk
            cache = get_cache("default")
            files = cache.get(cache_key)
            if not files:
                try:
                    store = Store(self.request.user)
                    toplist = store.toplist()
                    quota = store.get_quota()
                    files = {'toplist': toplist, 'quota': quota}
                except Exception:
                    logger.exception("Unable to get tolist for %s",
                                     unicode(self.request.user))
                    files = {'toplist': []}
                cache.set(cache_key, files, 300)

            context['files'] = files
        else:
            context['no_store'] = True

        return context


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
        if not request.user.has_perm('vm.access_console'):
            raise PermissionDenied()
        if self.object.node:
            with instance_activity(
                    code_suffix='console-accessed', instance=self.object,
                    user=request.user, readable_name=ugettext_noop(
                        "console access"), concurrency_check=False):
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
        user = self.request.user
        ops = get_operations(instance, user)
        context.update({
            'graphite_enabled': settings.GRAPHITE_URL is not None,
            'vnc_url': reverse_lazy("dashboard.views.detail-vnc",
                                    kwargs={'pk': self.object.pk}),
            'ops': ops,
            'op': {i.op: i for i in ops},
            'connect_commands': user.profile.get_connect_commands(instance)
        })

        # activity data
        activities = instance.get_merged_activities(user)
        show_show_all = len(activities) > 10
        activities = activities[:10]
        context['activities'] = _format_activities(activities)
        context['show_show_all'] = show_show_all
        latest = instance.get_latest_activity_in_progress()
        context['is_new_state'] = (latest and
                                   latest.resultant_state is not None and
                                   instance.status != latest.resultant_state)

        context['vlans'] = Vlan.get_objects_with_level(
            'user', self.request.user
        ).exclude(  # exclude already added interfaces
            pk__in=Interface.objects.filter(
                instance=self.get_object()).values_list("vlan", flat=True)
        ).all()
        context['acl'] = AclUpdateView.get_acl_data(
            instance, self.request.user, 'dashboard.views.vm-acl')
        context['aclform'] = AclUserAddForm()
        context['os_type_icon'] = instance.os_type.replace("unknown",
                                                           "question")
        # ipv6 infos
        context['ipv6_host'] = instance.get_connect_host(use_ipv6=True)
        context['ipv6_port'] = instance.get_connect_port(use_ipv6=True)

        # resources forms
        can_edit = (
            instance.has_level(user, "owner")
            and self.request.user.has_perm("vm.change_resources"))
        context['resources_form'] = VmResourcesForm(
            can_edit=can_edit, instance=instance)

        if self.request.user.is_superuser:
            context['traits_form'] = TraitsForm(instance=instance)
            context['raw_data_form'] = RawDataForm(instance=instance)

        # resources change perm
        context['can_change_resources'] = self.request.user.has_perm(
            "vm.change_resources")

        # can link template
        context['can_link_template'] = (
            instance.template and instance.template.has_level(user, "operator")
        )

        return context

    def post(self, request, *args, **kwargs):
        options = {
            'new_name': self.__set_name,
            'new_description': self.__set_description,
            'new_tag': self.__add_tag,
            'to_remove': self.__remove_tag,
            'port': self.__add_port,
            'abort_operation': self.__abort_operation,
        }
        for k, v in options.iteritems():
            if request.POST.get(k) is not None:
                return v(request)
        raise Http404()

    def __set_name(self, request):
        self.object = self.get_object()
        if not self.object.has_level(request.user, 'owner'):
            raise PermissionDenied()
        new_name = request.POST.get("new_name")
        Instance.objects.filter(pk=self.object.pk).update(
            **{'name': new_name})

        success_message = _("VM successfully renamed.")
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
            return redirect(self.object.get_absolute_url())

    def __set_description(self, request):
        self.object = self.get_object()
        if not self.object.has_level(request.user, 'owner'):
            raise PermissionDenied()

        new_description = request.POST.get("new_description")
        Instance.objects.filter(pk=self.object.pk).update(
            **{'description': new_description})

        success_message = _("VM description successfully updated.")
        if request.is_ajax():
            response = {
                'message': success_message,
                'new_description': new_description,
            }
            return HttpResponse(
                json.dumps(response),
                content_type="application/json"
            )
        else:
            messages.success(request, success_message)
            return redirect(self.object.get_absolute_url())

    def __add_tag(self, request):
        new_tag = request.POST.get('new_tag')
        self.object = self.get_object()
        if not self.object.has_level(request.user, 'owner'):
            raise PermissionDenied()

        if len(new_tag) < 1:
            message = u"Please input something."
        elif len(new_tag) > 20:
            message = u"Tag name is too long."
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
            error = _("There is a problem with your input.")
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

    def __abort_operation(self, request):
        self.object = self.get_object()

        activity = get_object_or_404(InstanceActivity,
                                     pk=request.POST.get("activity"))
        if not activity.is_abortable_for(request.user):
            raise PermissionDenied()
        activity.abort()
        return redirect("%s#activity" % self.object.get_absolute_url())


class VmTraitsUpdate(SuperuserRequiredMixin, UpdateView):
    form_class = TraitsForm
    model = Instance

    def get_success_url(self):
        return self.get_object().get_absolute_url() + "#resources"


class VmRawDataUpdate(SuperuserRequiredMixin, UpdateView):
    form_class = RawDataForm
    model = Instance
    template_name = 'dashboard/vm-detail/raw_data.html'

    def get_success_url(self):
        return self.get_object().get_absolute_url() + "#resources"


class OperationView(RedirectToLoginMixin, DetailView):

    template_name = 'dashboard/operate.html'
    show_in_toolbar = True
    effect = None
    wait_for_result = None
    with_reload = False

    @property
    def name(self):
        return self.get_op().name

    @property
    def description(self):
        return self.get_op().description

    def is_preferred(self):
        return self.get_op().is_preferred()

    @classmethod
    def get_urlname(cls):
        return 'dashboard.vm.op.%s' % cls.op

    @classmethod
    def get_instance_url(cls, pk, key=None, *args, **kwargs):
        url = reverse(cls.get_urlname(), args=(pk, ) + args, kwargs=kwargs)
        if key is None:
            return url
        else:
            return "%s?k=%s" % (url, key)

    def get_url(self, **kwargs):
        return self.get_instance_url(self.get_object().pk, **kwargs)

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/_modal.html']
        else:
            return ['dashboard/_base.html']

    @classmethod
    def get_op_by_object(cls, obj):
        return getattr(obj, cls.op)

    def get_op(self):
        if not hasattr(self, '_opobj'):
            setattr(self, '_opobj', getattr(self.get_object(), self.op))
        return self._opobj

    @classmethod
    def get_operation_class(cls):
        return cls.model.get_operation_class(cls.op)

    def get_context_data(self, **kwargs):
        ctx = super(OperationView, self).get_context_data(**kwargs)
        ctx['op'] = self.get_op()
        ctx['opview'] = self
        url = self.request.path
        if self.request.GET:
            url += '?' + self.request.GET.urlencode()
        ctx['url'] = url
        ctx['template'] = super(OperationView, self).get_template_names()[0]
        return ctx

    def check_auth(self):
        logger.debug("OperationView.check_auth(%s)", unicode(self))
        self.get_op().check_auth(self.request.user)

    @classmethod
    def check_perms(cls, user):
        cls.get_operation_class().check_perms(user)

    def get(self, request, *args, **kwargs):
        self.check_auth()
        return super(OperationView, self).get(request, *args, **kwargs)

    def get_response_data(self, result, done, extra=None, **kwargs):
        """Return serializable data to return to agents requesting json
        response to POST"""

        if extra is None:
            extra = {}
        extra["success"] = not isinstance(result, Exception)
        extra["done"] = done
        if isinstance(result, HumanReadableObject):
            extra["message"] = result.get_user_text()
        return extra

    def post(self, request, extra=None, *args, **kwargs):
        self.check_auth()
        self.object = self.get_object()
        if extra is None:
            extra = {}
        result = None
        done = False
        try:
            task = self.get_op().async(user=request.user, **extra)
        except HumanReadableException as e:
            e.send_message(request)
            logger.exception("Could not start operation")
            result = e
        except Exception as e:
            messages.error(request, _('Could not start operation.'))
            logger.exception("Could not start operation")
            result = e
        else:
            wait = self.wait_for_result
            if wait:
                try:
                    result = task.get(timeout=wait,
                                      interval=min((wait / 5, .5)))
                except TimeoutError:
                    logger.debug("Result didn't arrive in %ss",
                                 self.wait_for_result, exc_info=True)
                except HumanReadableException as e:
                    e.send_message(request)
                    logger.exception(e)
                    result = e
                except Exception as e:
                    messages.error(request, _('Operation failed.'))
                    logger.debug("Operation failed.", exc_info=True)
                    result = e
                else:
                    done = True
                    messages.success(request, _('Operation succeeded.'))
            if result is None and not done:
                messages.success(request, _('Operation is started.'))

        if "/json" in request.META.get("HTTP_ACCEPT", ""):
            data = self.get_response_data(result, done,
                                          post_extra=extra, **kwargs)
            return HttpResponse(json.dumps(data),
                                content_type="application/json")
        else:
            return redirect("%s#activity" % self.object.get_absolute_url())

    @classmethod
    def factory(cls, op, icon='cog', effect='info', extra_bases=(), **kwargs):
        kwargs.update({'op': op, 'icon': icon, 'effect': effect})
        return type(str(cls.__name__ + op),
                    tuple(list(extra_bases) + [cls]), kwargs)

    @classmethod
    def bind_to_object(cls, instance, **kwargs):
        me = cls()
        me.get_object = lambda: instance
        for key, value in kwargs.iteritems():
            setattr(me, key, value)
        return me


class AjaxOperationMixin(object):

    def post(self, request, extra=None, *args, **kwargs):
        resp = super(AjaxOperationMixin, self).post(
            request, extra, *args, **kwargs)
        if request.is_ajax():
            if not self.with_reload:
                store = messages.get_messages(request)
                store.used = True
            else:
                store = []
            return HttpResponse(
                json.dumps({'success': True,
                            'with_reload': self.with_reload,
                            'messages': [unicode(m) for m in store]}),
                content_type="application=json"
            )
        else:
            return resp


class VmOperationView(AjaxOperationMixin, OperationView):

    model = Instance
    context_object_name = 'instance'  # much simpler to mock object


class FormOperationMixin(object):

    form_class = None

    def get_form_kwargs(self):
        return {}

    def get_context_data(self, **kwargs):
        ctx = super(FormOperationMixin, self).get_context_data(**kwargs)
        if self.request.method == 'POST':
            ctx['form'] = self.form_class(self.request.POST,
                                          **self.get_form_kwargs())
        else:
            ctx['form'] = self.form_class(**self.get_form_kwargs())
        return ctx

    def post(self, request, extra=None, *args, **kwargs):
        if extra is None:
            extra = {}
        form = self.form_class(self.request.POST, **self.get_form_kwargs())
        if form.is_valid():
            extra.update(form.cleaned_data)
            resp = super(FormOperationMixin, self).post(
                request, extra, *args, **kwargs)
            if request.is_ajax():
                return HttpResponse(
                    json.dumps({
                        'success': True,
                        'with_reload': self.with_reload}),
                    content_type="application=json")
            else:
                return resp
        else:
            return self.get(request)


class RequestFormOperationMixin(FormOperationMixin):

    def get_form_kwargs(self):
        val = super(RequestFormOperationMixin, self).get_form_kwargs()
        val.update({'request': self.request})
        return val


class VmAddInterfaceView(FormOperationMixin, VmOperationView):

    op = 'add_interface'
    form_class = VmAddInterfaceForm
    show_in_toolbar = False
    icon = 'globe'
    effect = 'success'
    with_reload = True

    def get_form_kwargs(self):
        inst = self.get_op().instance
        choices = Vlan.get_objects_with_level(
            "user", self.request.user).exclude(
            vm_interface__instance__in=[inst])
        val = super(VmAddInterfaceView, self).get_form_kwargs()
        val.update({'choices': choices})
        return val


class VmCreateDiskView(FormOperationMixin, VmOperationView):

    op = 'create_disk'
    form_class = VmCreateDiskForm
    show_in_toolbar = False
    icon = 'hdd-o'
    effect = "success"
    is_disk_operation = True


class VmDownloadDiskView(FormOperationMixin, VmOperationView):

    op = 'download_disk'
    form_class = VmDownloadDiskForm
    show_in_toolbar = False
    icon = 'download'
    effect = "success"
    is_disk_operation = True


class VmMigrateView(VmOperationView):

    op = 'migrate'
    icon = 'truck'
    effect = 'info'
    template_name = 'dashboard/_vm-migrate.html'

    def get_context_data(self, **kwargs):
        ctx = super(VmMigrateView, self).get_context_data(**kwargs)
        ctx['nodes'] = [n for n in Node.objects.filter(enabled=True)
                        if n.state == "ONLINE"]
        return ctx

    def post(self, request, extra=None, *args, **kwargs):
        if extra is None:
            extra = {}
        node = self.request.POST.get("node")
        if node:
            node = get_object_or_404(Node, pk=node)
            extra["to_node"] = node
        return super(VmMigrateView, self).post(request, extra, *args, **kwargs)


class VmSaveView(FormOperationMixin, VmOperationView):

    op = 'save_as_template'
    icon = 'save'
    effect = 'info'
    form_class = VmSaveForm


class VmResourcesChangeView(VmOperationView):
    op = 'resources_change'
    icon = "save"
    show_in_toolbar = False
    wait_for_result = 0.5

    def post(self, request, extra=None, *args, **kwargs):
        if extra is None:
            extra = {}

        instance = get_object_or_404(Instance, pk=kwargs['pk'])

        form = VmResourcesForm(request.POST, instance=instance)
        if not form.is_valid():
            for f in form.errors:
                messages.error(request, "<strong>%s</strong>: %s" % (
                    f, form.errors[f].as_text()
                ))
            if request.is_ajax():  # this is not too nice
                store = messages.get_messages(request)
                store.used = True
                return HttpResponse(
                    json.dumps({'success': False,
                                'messages': [unicode(m) for m in store]}),
                    content_type="application=json"
                )
            else:
                return redirect(instance.get_absolute_url() + "#resources")
        else:
            extra = form.cleaned_data
            extra['max_ram_size'] = extra['ram_size']
            return super(VmResourcesChangeView, self).post(request, extra,
                                                           *args, **kwargs)


class TokenOperationView(OperationView):
    """Abstract operation view with token support.

    User can do the action with a valid token instead of logging in.
    """
    token_max_age = 3 * 24 * 3600
    redirect_exception_classes = (PermissionDenied, SuspiciousOperation, )

    @classmethod
    def get_salt(cls):
        return unicode(cls)

    @classmethod
    def get_token(cls, instance, user):
        t = tuple([getattr(i, 'pk', i) for i in [instance, user]])
        return signing.dumps(t, salt=cls.get_salt(), compress=True)

    @classmethod
    def get_token_url(cls, instance, user):
        key = cls.get_token(instance, user)
        return cls.get_instance_url(instance.pk, key)

    def check_auth(self):
        if 'k' in self.request.GET:
            try:  # check if token is needed at all
                return super(TokenOperationView, self).check_auth()
            except Exception:
                op = self.get_op()
                pk = op.instance.pk
                key = self.request.GET.get('k')

                logger.debug("checking token supplied to %s",
                             self.request.get_full_path())
                try:
                    user = self.validate_key(pk, key)
                except signing.SignatureExpired:
                    messages.error(self.request, _('The token has expired.'))
                else:
                    logger.info("Request user changed to %s at %s",
                                user, self.request.get_full_path())
                    self.request.user = user
                    self.request.token_user = True
        else:
            logger.debug("no token supplied to %s",
                         self.request.get_full_path())

        return super(TokenOperationView, self).check_auth()

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


class VmRenewView(FormOperationMixin, TokenOperationView, VmOperationView):

    op = 'renew'
    icon = 'calendar'
    effect = 'info'
    show_in_toolbar = False
    form_class = VmRenewForm
    wait_for_result = 0.5

    def get_form_kwargs(self):
        choices = Lease.get_objects_with_level("user", self.request.user)
        default = self.get_op().instance.lease
        if default and default not in choices:
            choices = (choices.distinct() |
                       Lease.objects.filter(pk=default.pk).distinct())

        val = super(VmRenewView, self).get_form_kwargs()
        val.update({'choices': choices, 'default': default})
        return val

    def get_response_data(self, result, done, extra=None, **kwargs):
        extra = super(VmRenewView, self).get_response_data(result, done,
                                                           extra, **kwargs)
        extra["new_suspend_time"] = unicode(self.get_op().
                                            instance.time_of_suspend)
        return extra


class VmStateChangeView(FormOperationMixin, VmOperationView):
    op = 'emergency_change_state'
    icon = 'legal'
    effect = 'danger'
    show_in_toolbar = True
    form_class = VmStateChangeForm
    wait_for_result = 0.5

    def get_form_kwargs(self):
        inst = self.get_op().instance
        active_activities = InstanceActivity.objects.filter(
            finished__isnull=True, instance=inst)
        show_interrupt = active_activities.exists()
        val = super(VmStateChangeView, self).get_form_kwargs()
        val.update({'show_interrupt': show_interrupt, 'status': inst.status})
        return val


vm_ops = OrderedDict([
    ('deploy', VmOperationView.factory(
        op='deploy', icon='play', effect='success')),
    ('wake_up', VmOperationView.factory(
        op='wake_up', icon='sun-o', effect='success')),
    ('sleep', VmOperationView.factory(
        extra_bases=[TokenOperationView],
        op='sleep', icon='moon-o', effect='info')),
    ('migrate', VmMigrateView),
    ('save_as_template', VmSaveView),
    ('reboot', VmOperationView.factory(
        op='reboot', icon='refresh', effect='warning')),
    ('reset', VmOperationView.factory(
        op='reset', icon='bolt', effect='warning')),
    ('shutdown', VmOperationView.factory(
        op='shutdown', icon='power-off', effect='warning')),
    ('shut_off', VmOperationView.factory(
        op='shut_off', icon='ban', effect='warning')),
    ('recover', VmOperationView.factory(
        op='recover', icon='medkit', effect='warning')),
    ('nostate', VmStateChangeView),
    ('destroy', VmOperationView.factory(
        extra_bases=[TokenOperationView],
        op='destroy', icon='times', effect='danger')),
    ('create_disk', VmCreateDiskView),
    ('download_disk', VmDownloadDiskView),
    ('add_interface', VmAddInterfaceView),
    ('renew', VmRenewView),
    ('resources_change', VmResourcesChangeView),
    ('password_reset', VmOperationView.factory(
        op='password_reset', icon='unlock', effect='warning',
        show_in_toolbar=False, wait_for_result=0.5, with_reload=True)),
    ('mount_store', VmOperationView.factory(
        op='mount_store', icon='briefcase', effect='info',
        show_in_toolbar=False,
    )),
])


def get_operations(instance, user):
    ops = []
    for k, v in vm_ops.iteritems():
        try:
            op = v.get_op_by_object(instance)
            op.check_auth(user)
            op.check_precond()
        except PermissionDenied as e:
            logger.debug('Not showing operation %s for %s: %s',
                         k, instance, unicode(e))
        except Exception:
            ops.append(v.bind_to_object(instance, disabled=True))
        else:
            ops.append(v.bind_to_object(instance))
    return ops


class MassOperationView(OperationView):
    template_name = 'dashboard/mass-operate.html'

    def check_auth(self):
        self.get_op().check_perms(self.request.user)
        for i in self.get_object():
            if not i.has_level(self.request.user, "user"):
                raise PermissionDenied(
                    "You have no user access to instance %d" % i.pk)

    @classmethod
    def get_urlname(cls):
        return 'dashboard.vm.mass-op.%s' % cls.op

    @classmethod
    def get_url(cls):
        return reverse("dashboard.vm.mass-op.%s" % cls.op)

    def get_op(self, instance=None):
        if instance:
            return getattr(instance, self.op)
        else:
            return Instance._ops[self.op]

    def get_context_data(self, **kwargs):
        ctx = super(MassOperationView, self).get_context_data(**kwargs)
        instances = self.get_object()
        ctx['instances'] = self._get_operable_instances(
            instances, self.request.user)
        ctx['vm_count'] = sum(1 for i in ctx['instances'] if not i.disabled)
        return ctx

    def _call_operations(self, extra):
        request = self.request
        user = request.user
        instances = self.get_object()
        for i in instances:
            try:
                self.get_op(i).async(user=user, **extra)
            except HumanReadableException as e:
                e.send_message(request)
            except Exception as e:
                # pre-existing errors should have been catched when the
                # confirmation dialog was constructed
                messages.error(request, _(
                    "Failed to execute %(op)s operation on "
                    "instance %(instance)s.") % {"op": self.name,
                                                 "instance": i})

    def get_object(self):
        vms = getattr(self.request, self.request.method).getlist("vm")
        return Instance.objects.filter(pk__in=vms)

    def _get_operable_instances(self, instances, user):
        for i in instances:
            try:
                op = self.get_op(i)
                op.check_auth(user)
                op.check_precond()
            except PermissionDenied as e:
                i.disabled = create_readable(
                    _("You are not permitted to execute %(op)s on instance "
                      "%(instance)s."), instance=i.pk, op=self.name)
                i.disabled_icon = "lock"
            except Exception as e:
                i.disabled = fetch_human_exception(e)
            else:
                i.disabled = None
        return instances

    def post(self, request, extra=None, *args, **kwargs):
        self.check_auth()
        if extra is None:
            extra = {}
        self._call_operations(extra)
        if request.is_ajax():
            store = messages.get_messages(request)
            store.used = True
            return HttpResponse(
                json.dumps({'messages': [unicode(m) for m in store]}),
                content_type="application/json"
            )
        else:
            return redirect(reverse("dashboard.views.vm-list"))

    @classmethod
    def factory(cls, vm_op, extra_bases=(), **kwargs):
        return type(str(cls.__name__ + vm_op.op),
                    tuple(list(extra_bases) + [cls, vm_op]), kwargs)


class MassMigrationView(MassOperationView, VmMigrateView):
    template_name = 'dashboard/_vm-mass-migrate.html'

vm_mass_ops = OrderedDict([
    ('deploy', MassOperationView.factory(vm_ops['deploy'])),
    ('wake_up', MassOperationView.factory(vm_ops['wake_up'])),
    ('sleep', MassOperationView.factory(vm_ops['sleep'])),
    ('reboot', MassOperationView.factory(vm_ops['reboot'])),
    ('reset', MassOperationView.factory(vm_ops['reset'])),
    ('shut_off', MassOperationView.factory(vm_ops['shut_off'])),
    ('migrate', MassMigrationView),
    ('destroy', MassOperationView.factory(vm_ops['destroy'])),
])


class NodeDetailView(LoginRequiredMixin, SuperuserRequiredMixin, DetailView):
    template_name = "dashboard/node-detail.html"
    model = Node
    form = None
    form_class = TraitForm

    def get_context_data(self, form=None, **kwargs):
        if form is None:
            form = self.form_class()
        context = super(NodeDetailView, self).get_context_data(**kwargs)
        na = NodeActivity.objects.filter(
            node=self.object, parent=None
        ).order_by('-started').select_related()
        context['activities'] = na
        context['trait_form'] = form
        context['graphite_enabled'] = (
            settings.GRAPHITE_URL is not None)
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

        success_message = _("Node successfully renamed.")
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
    read_level = 'operator'

    def get_has_level(self):
        return self.object.profile.has_level

    def get_context_data(self, **kwargs):
        context = super(GroupDetailView, self).get_context_data(**kwargs)
        context['group'] = self.object
        context['users'] = self.object.user_set.all()
        context['future_users'] = FutureMember.objects.filter(
            group=self.object)
        context['acl'] = AclUpdateView.get_acl_data(
            self.object.profile, self.request.user,
            'dashboard.views.group-acl')
        context['aclform'] = AclUserAddForm()
        context['group_profile_form'] = GroupProfileUpdate.get_form_object(
            self.request, self.object.profile)

        if self.request.user.is_superuser:
            context['group_perm_form'] = GroupPermissionForm(
                instance=self.object)

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.get_has_level()(request.user, 'operator'):
            raise PermissionDenied()

        if request.POST.get('new_name'):
            return self.__set_name(request)
        if request.POST.get('list-new-name'):
            return self.__add_user(request)
        if request.POST.get('list-new-namelist'):
            return self.__add_list(request)
        if (request.POST.get('list-new-name') is not None) and \
                (request.POST.get('list-new-namelist') is not None):
            return redirect(reverse_lazy("dashboard.views.group-detail",
                                         kwargs={'pk': self.get_object().pk}))

    def __add_user(self, request):
        name = request.POST['list-new-name']
        self.__add_username(request, name)
        return redirect(reverse_lazy("dashboard.views.group-detail",
                                     kwargs={'pk': self.object.pk}))

    def __add_username(self, request, name):
        if not name:
            return
        try:
            entity = search_user(name)
            self.object.user_set.add(entity)
        except User.DoesNotExist:
            if saml_available:
                FutureMember.objects.get_or_create(org_id=name,
                                                   group=self.object)
            else:
                messages.warning(request, _('User "%s" not found.') % name)

    def __add_list(self, request):
        if not self.get_has_level()(request.user, 'operator'):
            raise PermissionDenied()
        userlist = request.POST.get('list-new-namelist').split('\r\n')
        for line in userlist:
            self.__add_username(request, line)
        return redirect(reverse_lazy("dashboard.views.group-detail",
                                     kwargs={'pk': self.object.pk}))

    def __set_name(self, request):
        new_name = request.POST.get("new_name")
        Group.objects.filter(pk=self.object.pk).update(
            **{'name': new_name})

        success_message = _("Group successfully renamed.")
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


class GroupPermissionsView(SuperuserRequiredMixin, UpdateView):
    model = Group
    form_class = GroupPermissionForm
    slug_field = "pk"
    slug_url_kwarg = "group_pk"

    def get_success_url(self):
        return "%s#group-detail-permissions" % (
            self.get_object().groupprofile.get_absolute_url())


class AclUpdateView(LoginRequiredMixin, View, SingleObjectMixin):
    def send_success_message(self, whom, old_level, new_level):
        if old_level and new_level:
            msg = _("Acl user/group %(w)s successfully modified.")
        elif not old_level and new_level:
            msg = _("Acl user/group %(w)s successfully added.")
        elif old_level and not new_level:
            msg = _("Acl user/group %(w)s successfully removed.")
        if msg:
            messages.success(self.request, msg % {'w': whom})

    def get_level(self, whom):
        for u, level in self.acl_data:
            if u == whom:
                return level
        return None

    @classmethod
    def get_acl_data(cls, obj, user, url):
        levels = obj.ACL_LEVELS
        allowed_levels = list(l for l in OrderedDict(levels)
                              if cls.has_next_level(user, obj, l))
        is_owner = 'owner' in allowed_levels

        allowed_users = cls.get_allowed_users(user)
        allowed_groups = cls.get_allowed_groups(user)

        user_levels = list(
            {'user': u, 'level': l} for u, l in obj.get_users_with_level()
            if is_owner or u == user or u in allowed_users)

        group_levels = list(
            {'group': g, 'level': l} for g, l in obj.get_groups_with_level()
            if is_owner or g in allowed_groups)

        return {'users': user_levels,
                'groups': group_levels,
                'levels': levels,
                'allowed_levels': allowed_levels,
                'url': reverse(url, args=[obj.pk])}

    @classmethod
    def has_next_level(self, user, instance, level):
        levels = OrderedDict(instance.ACL_LEVELS).keys()
        next_levels = dict(zip([None] + levels, levels + levels[-1:]))
        # {None: 'user', 'user': 'operator', 'operator: 'owner',
        #  'owner: 'owner'}
        next_level = next_levels[level]
        return instance.has_level(user, next_level)

    @classmethod
    def get_allowed_groups(cls, user):
        if user.has_perm('dashboard.use_autocomplete'):
            return Group.objects.all()
        else:
            profiles = GroupProfile.get_objects_with_level('owner', user)
            return Group.objects.filter(groupprofile__in=profiles).distinct()

    @classmethod
    def get_allowed_users(cls, user):
        if user.has_perm('dashboard.use_autocomplete'):
            return User.objects.all()
        else:
            groups = cls.get_allowed_groups(user)
            return User.objects.filter(
                Q(groups__in=groups) | Q(pk=user.pk)).distinct()

    def check_auth(self, whom, old_level, new_level):
        if isinstance(whom, Group):
            if (not self.is_owner and whom not in
                    AclUpdateView.get_allowed_groups(self.request.user)):
                return False
        elif isinstance(whom, User):
            if (not self.is_owner and whom not in
                    AclUpdateView.get_allowed_users(self.request.user)):
                return False
        return (
            AclUpdateView.has_next_level(self.request.user,
                                         self.instance, new_level) and
            AclUpdateView.has_next_level(self.request.user,
                                         self.instance, old_level))

    def set_level(self, whom, new_level):
        user = self.request.user
        old_level = self.get_level(whom)
        if old_level == new_level:
            return

        if getattr(self.instance, "owner", None) == whom:
            logger.info("Tried to set owner's acl level for %s by %s.",
                        unicode(self.instance), unicode(user))
            msg = _("The original owner cannot be removed, however "
                    "you can transfer ownership.")
            if not getattr(self, 'hide_messages', False):
                messages.warning(self.request, msg)
        elif self.check_auth(whom, old_level, new_level):
            logger.info(
                u"Set %s's acl level for %s to %s by %s.", unicode(whom),
                unicode(self.instance), new_level, unicode(user))
            if not getattr(self, 'hide_messages', False):
                self.send_success_message(whom, old_level, new_level)
            self.instance.set_level(whom, new_level)
        else:
            logger.warning(
                u"Tried to set %s's acl_level for %s (%s->%s) by %s.",
                unicode(whom), unicode(self.instance), old_level, new_level,
                unicode(user))

    def set_or_remove_levels(self):
        for key, value in self.request.POST.items():
            m = re.match('(perm|remove)-([ug])-(\d+)', key)
            if m:
                cmd, typ, id = m.groups()
                if cmd == 'remove':
                    value = None
                entity = {'u': User, 'g': Group}[typ].objects.get(id=id)
                self.set_level(entity, value)

    def add_levels(self):
        name = self.request.POST.get('name', None)
        level = self.request.POST.get('level', None)
        if not name or not level:
            return
        try:
            entity = search_user(name)
            if self.instance.object_level_set.filter(users__in=[entity]):
                messages.warning(
                    self.request, _('User "%s" has already '
                                    'access to this object.') % name)
                return
        except User.DoesNotExist:
            entity = None
            try:
                entity = Group.objects.get(name=name)
                if self.instance.object_level_set.filter(groups__in=[entity]):
                    messages.warning(
                        self.request, _('Group "%s" has already '
                                        'access to this object.') % name)
                    return
            except Group.DoesNotExist:
                messages.warning(
                    self.request, _('User or group "%s" not found.') % name)
                return
        self.set_level(entity, level)

    def post(self, request, *args, **kwargs):
        self.instance = self.get_object()
        self.is_owner = self.instance.has_level(request.user, 'owner')
        self.acl_data = (self.instance.get_users_with_level() +
                         self.instance.get_groups_with_level())
        self.set_or_remove_levels()
        self.add_levels()
        return redirect("%s#access" % self.instance.get_absolute_url())


class TemplateAclUpdateView(AclUpdateView):
    model = InstanceTemplate


class GroupAclUpdateView(AclUpdateView):
    model = Group

    def get_object(self):
        return super(GroupAclUpdateView, self).get_object().profile


class TemplateChoose(LoginRequiredMixin, TemplateView):

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/modal-wrapper.html']
        else:
            return ['dashboard/nojs-wrapper.html']

    def get_context_data(self, *args, **kwargs):
        context = super(TemplateChoose, self).get_context_data(*args, **kwargs)
        templates = InstanceTemplate.get_objects_with_level("user",
                                                            self.request.user)
        context.update({
            'box_title': _('Choose template'),
            'ajax_title': True,
            'template': "dashboard/_template-choose.html",
            'templates': templates.all(),
        })
        return context

    def post(self, request, *args, **kwargs):
        if not request.user.has_perm('vm.create_template'):
            raise PermissionDenied()

        template = request.POST.get("parent")
        if template == "base_vm":
            return redirect(reverse("dashboard.views.template-create"))
        elif template is None:
            messages.warning(request, _("Select an option to proceed."))
            return redirect(reverse("dashboard.views.template-choose"))
        else:
            template = get_object_or_404(InstanceTemplate, pk=template)

        if not template.has_level(request.user, "user"):
            raise PermissionDenied()

        instance = Instance.create_from_template(
            template=template, owner=request.user, is_base=True)

        return redirect(instance.get_absolute_url())


class TemplateCreate(SuccessMessageMixin, CreateView):
    model = InstanceTemplate
    form_class = TemplateForm

    def get_template_names(self):
        if self.request.is_ajax():
            pass
        else:
            return ['dashboard/nojs-wrapper.html']

    def get_context_data(self, *args, **kwargs):
        context = super(TemplateCreate, self).get_context_data(*args, **kwargs)

        num_leases = Lease.get_objects_with_level("operator",
                                                  self.request.user).count()
        can_create_leases = self.request.user.has_perm("create_leases")
        context.update({
            'box_title': _("Create a new base VM"),
            'template': "dashboard/_template-create.html",
            'show_lease_create': num_leases < 1 and can_create_leases
        })
        return context

    def get(self, *args, **kwargs):
        if not self.request.user.has_perm('vm.create_base_template'):
            raise PermissionDenied()

        return super(TemplateCreate, self).get(*args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(TemplateCreate, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def post(self, request, *args, **kwargs):
        if not self.request.user.has_perm('vm.create_base_template'):
            raise PermissionDenied()

        form = self.form_class(request.POST, user=request.user)
        if not form.is_valid():
            return self.get(request, form, *args, **kwargs)
        else:
            post = form.cleaned_data
            networks = self.__create_networks(post.pop("networks"),
                                              request.user)
            post.pop("parent")
            post['max_ram_size'] = post['ram_size']
            req_traits = post.pop("req_traits")
            tags = post.pop("tags")
            post['pw'] = User.objects.make_random_password()
            post['is_base'] = True
            inst = Instance.create(params=post, disks=[],
                                   networks=networks,
                                   tags=tags, req_traits=req_traits)

            return redirect("%s#resources" % inst.get_absolute_url())

    def __create_networks(self, vlans, user):
        networks = []
        for v in vlans:
            if not v.has_level(user, "user"):
                raise PermissionDenied()
            networks.append(InterfaceTemplate(vlan=v, managed=v.managed))
        return networks

    def get_success_url(self):
        return reverse_lazy("dashboard.views.template-list")


class TemplateDetail(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = InstanceTemplate
    template_name = "dashboard/template-edit.html"
    form_class = TemplateForm
    success_message = _("Successfully modified template.")

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
        context['acl'] = AclUpdateView.get_acl_data(
            obj, self.request.user, 'dashboard.views.template-acl')
        context['disks'] = obj.disks.all()
        context['is_owner'] = obj.has_level(self.request.user, 'owner')
        context['aclform'] = AclUserAddForm()
        return context

    def get_success_url(self):
        return reverse_lazy("dashboard.views.template-detail",
                            kwargs=self.kwargs)

    def post(self, request, *args, **kwargs):
        template = self.get_object()
        if not template.has_level(request.user, 'owner'):
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
        context['lease_table'] = LeaseListTable(Lease.objects.all(),
                                                request=self.request)
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

        object.destroy_disks()
        object.delete()
        success_url = self.get_success_url()
        success_message = _("Template successfully deleted.")

        if request.is_ajax():
            return HttpResponse(
                json.dumps({'message': success_message}),
                content_type="application/json",
            )
        else:
            messages.success(request, success_message)
            return HttpResponseRedirect(success_url)


class VmList(LoginRequiredMixin, FilterMixin, ListView):
    template_name = "dashboard/vm-list.html"
    allowed_filters = {
        'name': "name__icontains",
        'node': "node__name__icontains",
        'status': "status__iexact",
        'tags[]': "tags__name__in",
        'tags': "tags__name__in",  # for search string
        'owner': "owner__username",
        'template': "template__pk",
    }

    def get_context_data(self, *args, **kwargs):
        context = super(VmList, self).get_context_data(*args, **kwargs)
        context['ops'] = []
        for k, v in vm_mass_ops.iteritems():
            try:
                v.check_perms(user=self.request.user)
            except PermissionDenied:
                pass
            else:
                context['ops'].append(v)
        context['search_form'] = self.search_form
        return context

    def get(self, *args, **kwargs):
        if self.request.is_ajax():
            return self._create_ajax_request()
        else:
            self.search_form = VmListSearchForm(self.request.GET)
            self.search_form.full_clean()
            return super(VmList, self).get(*args, **kwargs)

    def _create_ajax_request(self):
        if self.request.GET.get("compact") is not None:
            instances = Instance.get_objects_with_level(
                "user", self.request.user).filter(destroyed_at=None)
            statuses = {}
            for i in instances:
                statuses[i.pk] = {
                    'status': i.get_status_display(),
                    'icon': i.get_status_icon(),
                    'in_status_change': i.is_in_status_change(),
                }
                if self.request.user.is_superuser:
                    statuses[i.pk]['node'] = i.node.name if i.node else "-"
            return HttpResponse(json.dumps(statuses),
                                content_type="application/json")
        else:
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
                'fav': i.pk in favs,
            } for i in instances]
            return HttpResponse(
                json.dumps(list(instances)),  # instances is ValuesQuerySet
                content_type="application/json",
            )

    def get_queryset(self):
        logger.debug('VmList.get_queryset() called. User: %s',
                     unicode(self.request.user))
        queryset = self.create_default_queryset()

        self.create_fake_get()
        sort = self.request.GET.get("sort")
        # remove "-" that means descending order
        # also check if the column name is valid
        if (sort and
            (sort[1:] if sort[0] == "-" else sort)
                in [i.name for i in Instance._meta.fields] + ["pk"]):
            queryset = queryset.order_by(sort)

        return queryset.filter(
            **self.get_queryset_filters()).select_related('owner', 'node'
                                                          ).distinct()

    def create_default_queryset(self):
        cleaned_data = self.search_form.cleaned_data
        stype = cleaned_data.get('stype', "all")
        superuser = stype == "all"
        shared = stype == "shared"
        level = "owner" if stype == "owned" else "user"
        queryset = Instance.get_objects_with_level(
            level, self.request.user,
            group_also=shared, disregard_superuser=not superuser,
        ).filter(destroyed_at=None)
        return queryset

    def create_fake_get(self):
        """
        Updates the request's GET dict to filter the vm list
        For example: "name:xy node:1" updates the GET dict
                     to resemble this URL ?name=xy&node=1

        "name:xy node:1".split(":") becomes ["name", "xy node", "1"]
        we pop the the first element and use it as the first dict key
        then we iterate over the rest of the list and split by the last
        whitespace, the first part of this list will be the previous key's
        value, then last part of the list will be the next key.
        The final dict looks like this: {'name': xy, 'node':1}
        """
        s = self.request.GET.get("s")
        if s:
            s = s.split(":")
            if len(s) < 2:  # if there is no ':' in the string, filter by name
                got = {'name': s[0]}
            else:
                latest = s.pop(0)
                got = {'%s' % latest: None}
                for i in s[:-1]:
                    new = i.rsplit(" ", 1)
                    got[latest] = new[0]
                    latest = new[1] if len(new) > 1 else None
                got[latest] = s[-1]

            # generate a new GET request, that is kinda fake
            fake = self.request.GET.copy()
            for k, v in got.iteritems():
                fake[k] = v

            self.request.GET = fake


class NodeList(LoginRequiredMixin, SuperuserRequiredMixin, SingleTableView):
    template_name = "dashboard/node-list.html"
    table_class = NodeListTable
    table_pagination = False

    def get(self, *args, **kwargs):
        if self.request.is_ajax():
            nodes = Node.objects.all()
            nodes = [{
                'name': i.name,
                'icon': i.get_status_icon(),
                'url': i.get_absolute_url(),
                'label': i.get_status_label(),
                'status': i.state.lower()} for i in nodes]

            return HttpResponse(
                json.dumps(list(nodes)),
                content_type="application/json",
            )
        else:
            return super(NodeList, self).get(*args, **kwargs)

    def get_queryset(self):
        return Node.objects.annotate(
            number_of_VMs=Count('instance_set')).select_related('host')


class GroupList(LoginRequiredMixin, SingleTableView):
    template_name = "dashboard/group-list.html"
    model = Group
    table_class = GroupListTable
    table_pagination = False

    def get(self, *args, **kwargs):
        if self.request.is_ajax():
            groups = [{
                'url': reverse("dashboard.views.group-detail",
                               kwargs={'pk': i.pk}),
                'name': i.name} for i in self.get_queryset()]
            return HttpResponse(
                json.dumps(list(groups)),
                content_type="application/json",
            )
        else:
            return super(GroupList, self).get(*args, **kwargs)

    def get_queryset(self):
        logger.debug('GroupList.get_queryset() called. User: %s',
                     unicode(self.request.user))
        profiles = GroupProfile.get_objects_with_level(
            'operator', self.request.user)
        groups = Group.objects.filter(groupprofile__in=profiles)
        s = self.request.GET.get("s")
        if s:
            groups = groups.filter(name__icontains=s)
        return groups


class GroupRemoveUserView(CheckedDetailView, DeleteView):
    model = Group
    slug_field = 'pk'
    slug_url_kwarg = 'group_pk'
    read_level = 'operator'
    member_key = 'member_pk'

    def get_has_level(self):
        return self.object.profile.has_level

    def get_context_data(self, **kwargs):
        context = super(GroupRemoveUserView, self).get_context_data(**kwargs)
        try:
            context['member'] = User.objects.get(pk=self.member_pk)
        except User.DoesNotExist:
            raise Http404()
        return context

    def get_success_url(self):
        next = self.request.POST.get('next')
        if next:
            return next
        else:
            return reverse_lazy("dashboard.views.group-detail",
                                kwargs={'pk': self.get_object().pk})

    def get(self, request, member_pk, *args, **kwargs):
        self.member_pk = member_pk
        return super(GroupRemoveUserView, self).get(request, *args, **kwargs)

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/confirm/ajax-remove.html']
        else:
            return ['dashboard/confirm/base-remove.html']

    def remove_member(self, pk):
        container = self.get_object()
        container.user_set.remove(User.objects.get(pk=pk))

    def get_success_message(self):
        return _("Member successfully removed from group.")

    def delete(self, request, *args, **kwargs):
        object = self.get_object()
        if not object.profile.has_level(request.user, 'operator'):
            raise PermissionDenied()
        self.remove_member(kwargs[self.member_key])
        success_url = self.get_success_url()
        success_message = self.get_success_message()
        if request.is_ajax():
            return HttpResponse(
                json.dumps({'message': success_message}),
                content_type="application/json",
            )
        else:
            messages.success(request, success_message)
            return HttpResponseRedirect(success_url)


class GroupRemoveFutureUserView(GroupRemoveUserView):

    member_key = 'member_org_id'

    def get(self, request, member_org_id, *args, **kwargs):
        self.member_org_id = member_org_id
        return super(GroupRemoveUserView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(GroupRemoveUserView, self).get_context_data(**kwargs)
        try:
            context['member'] = FutureMember.objects.get(
                org_id=self.member_org_id, group=self.get_object())
        except FutureMember.DoesNotExist:
            raise Http404()
        return context

    def remove_member(self, org_id):
        FutureMember.objects.filter(org_id=org_id,
                                    group=self.get_object()).delete()

    def get_success_message(self):
        return _("Future user successfully removed from group.")


class GroupDelete(CheckedDetailView, DeleteView):

    """This stuff deletes the group.
    """
    model = Group
    template_name = "dashboard/confirm/base-delete.html"
    read_level = 'operator'

    def get_has_level(self):
        return self.object.profile.has_level

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/confirm/ajax-delete.html']
        else:
            return ['dashboard/confirm/base-delete.html']

    # github.com/django/django/blob/master/django/views/generic/edit.py#L245
    def delete(self, request, *args, **kwargs):
        object = self.get_object()
        if not object.profile.has_level(request.user, 'owner'):
            raise PermissionDenied()
        object.delete()
        success_url = self.get_success_url()
        success_message = _("Group successfully deleted.")

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
        if not request.user.has_perm('vm.create_vm'):
            raise PermissionDenied()

        form_error = form is not None
        template = (form.template.pk if form_error
                    else request.GET.get("template"))
        templates = InstanceTemplate.get_objects_with_level(
            'user', request.user, disregard_superuser=True)
        if form is None and template:
            form = self.form_class(user=request.user,
                                   template=templates.get(pk=template))

        context = self.get_context_data(**kwargs)
        if template:
            context.update({
                'template': 'dashboard/_vm-create-2.html',
                'box_title': _('Customize VM'),
                'ajax_title': True,
                'vm_create_form': form,
                'template_o': templates.get(pk=template),
            })
        else:
            context.update({
                'template': 'dashboard/_vm-create-1.html',
                'box_title': _('Create a VM'),
                'ajax_title': True,
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

        args = {"template": template, "owner": user}
        if "name" in request.POST:
            args["name"] = request.POST.get("name")
        instances = [Instance.create_from_template(**args)]
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
                'max_ram_size': post['ram_size'],
            }
            networks = [InterfaceTemplate(vlan=l, managed=l.managed)
                        for l in post['networks']]

            ikwargs.update({
                'template': template,
                'owner': user,
                'networks': networks,
                'disks': list(template.disks.all()),
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
            messages.success(request, ungettext_lazy(
                "Successfully created %(count)d VM.",  # this should not happen
                "Successfully created %(count)d VMs.", len(instances)) % {
                'count': len(instances)})
            path = "%s?stype=owned" % reverse("dashboard.views.vm-list")
        else:
            messages.success(request, _("VM successfully created."))
            path = instances[0].get_absolute_url()

        if request.is_ajax():
            return HttpResponse(json.dumps({'redirect': path}),
                                content_type="application/json")
        else:
            return redirect("%s#activity" % path)

    def post(self, request, *args, **kwargs):
        user = request.user

        if not request.user.has_perm('vm.create_vm'):
            raise PermissionDenied()

        # limit chekcs
        try:
            limit = user.profile.instance_limit
        except Exception as e:
            logger.debug('No profile or instance limit: %s', e)
        else:
            try:
                amount = int(request.POST.get("amount", 1))
            except:
                amount = limit  # TODO this should definitely use a Form
            current = Instance.active.filter(owner=user).count()
            logger.debug('current use: %d, limit: %d', current, limit)
            if current + amount > limit:
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
        messages.success(request, _('Node successfully created.'))
        path = nodemodel[0].get_absolute_url()
        if request.is_ajax():
            return HttpResponse(json.dumps({'redirect': path}),
                                content_type="application/json")
        else:
            return redirect(path)


class GroupCreate(GroupCodeMixin, LoginRequiredMixin, TemplateView):

    form_class = GroupCreateForm

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/modal-wrapper.html']
        else:
            return ['dashboard/nojs-wrapper.html']

    def get(self, request, form=None, *args, **kwargs):
        if not request.user.has_module_perms('auth'):
            raise PermissionDenied()
        if form is None:
            form = self.form_class(
                new_groups=self.get_available_group_codes(request))
        context = self.get_context_data(**kwargs)
        context.update({
            'template': 'dashboard/group-create.html',
            'box_title': _('Create a Group'),
            'form': form,
            'ajax_title': True,
        })
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        if not request.user.has_module_perms('auth'):
            raise PermissionDenied()
        form = self.form_class(
            request.POST, new_groups=self.get_available_group_codes(request))
        if not form.is_valid():
            return self.get(request, form, *args, **kwargs)
        form.cleaned_data
        savedform = form.save()
        savedform.profile.set_level(request.user, 'owner')
        messages.success(request, _('Group successfully created.'))
        if request.is_ajax():
            return HttpResponse(json.dumps({'redirect':
                                savedform.profile.get_absolute_url()}),
                                content_type="application/json")
        else:
            return redirect(savedform.profile.get_absolute_url())


class GroupProfileUpdate(SuccessMessageMixin, GroupCodeMixin,
                         LoginRequiredMixin, UpdateView):

    form_class = GroupProfileUpdateForm
    model = Group
    success_message = _('Group is successfully updated.')

    @classmethod
    def get_available_group_codes(cls, request, extra=None):
        result = super(GroupProfileUpdate, cls).get_available_group_codes(
            request)
        if extra and extra not in result:
            result += [extra]
        return result

    def get_object(self):
        group = super(GroupProfileUpdate, self).get_object()
        profile = group.profile
        if not profile.has_level(self.request.user, 'owner'):
            raise PermissionDenied
        else:
            return profile

    @classmethod
    def get_form_object(cls, request, instance, *args, **kwargs):
        kwargs['instance'] = instance
        kwargs['new_groups'] = cls.get_available_group_codes(
            request, instance.org_id)
        kwargs['superuser'] = request.user.is_superuser
        return cls.form_class(*args, **kwargs)

    def get(self, request, form=None, *args, **kwargs):
        self.object = self.get_object()
        if form is None:
            form = self.get_form_object(request, self.object)
        return super(GroupProfileUpdate, self).get(
            request, form, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not request.user.has_module_perms('auth'):
            raise PermissionDenied()
        self.object = self.get_object()
        form = self.get_form_object(request, self.object, self.request.POST)
        if not form.is_valid():
            return self.form_invalid(form)
        form.save()
        return self.form_valid(form)


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

    # github.com/django/django/blob/master/django/views/generic/edit.py#L245
    def delete(self, request, *args, **kwargs):
        object = self.get_object()

        object.delete()
        success_url = self.get_success_url()
        success_message = _("Node successfully deleted.")

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
        success_message = _("Node successfully changed status.")

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
        success_message = _("Node successfully flushed.")
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
        success_message = _("Port successfully removed.")

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


class LeaseCreate(LoginRequiredMixin, PermissionRequiredMixin,
                  SuccessMessageMixin, CreateView):
    model = Lease
    form_class = LeaseForm
    permission_required = 'vm.create_leases'
    template_name = "dashboard/lease-create.html"
    success_message = _("Successfully created a new lease.")

    def get_success_url(self):
        return reverse_lazy("dashboard.views.template-list")


class LeaseAclUpdateView(AclUpdateView):
    model = Lease


class LeaseDetail(LoginRequiredMixin, SuperuserRequiredMixin,
                  SuccessMessageMixin, UpdateView):
    model = Lease
    form_class = LeaseForm
    template_name = "dashboard/lease-edit.html"
    success_message = _("Successfully modified lease.")

    def get_context_data(self, *args, **kwargs):
        obj = self.get_object()
        context = super(LeaseDetail, self).get_context_data(*args, **kwargs)
        context['acl'] = AclUpdateView.get_acl_data(
            obj, self.request.user, 'dashboard.views.lease-acl')
        return context

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

    def get_context_data(self, *args, **kwargs):
        c = super(LeaseDelete, self).get_context_data(*args, **kwargs)
        lease = self.get_object()
        templates = lease.instancetemplate_set
        if templates.count() > 0:
            text = _("You can't delete this lease because some templates "
                     "are still using it, modify these to proceed: ")

            c['text'] = text + ", ".join("<strong>%s (#%d)</strong>"
                                         "" % (o.name, o.pk)
                                         for o in templates.all())
            c['disable_submit'] = True
        return c

    def delete(self, request, *args, **kwargs):
        object = self.get_object()

        if (object.instancetemplate_set.count() > 0):
            raise SuspiciousOperation()

        object.delete()
        success_url = self.get_success_url()
        success_message = _("Lease successfully deleted.")

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
    if not instance.has_level(request.user, 'user'):
        raise PermissionDenied()

    response = {}
    show_all = request.GET.get("show_all", "false") == "true"
    activities = _format_activities(
        instance.get_merged_activities(request.user))
    show_show_all = len(activities) > 10
    if not show_all:
        activities = activities[:10]

    response['human_readable_status'] = instance.get_status_display()
    response['status'] = instance.status
    response['icon'] = instance.get_status_icon()
    latest = instance.get_latest_activity_in_progress()
    response['is_new_state'] = (latest and latest.resultant_state is not None
                                and instance.status != latest.resultant_state)

    context = {
        'instance': instance,
        'activities': activities,
        'show_show_all': show_show_all,
        'ops': get_operations(instance, request.user),
    }

    response['activities'] = render_to_string(
        "dashboard/vm-detail/_activity-timeline.html",
        RequestContext(request, context),
    )
    response['ops'] = render_to_string(
        "dashboard/vm-detail/_operations.html",
        RequestContext(request, context),
    )
    response['disk_ops'] = render_to_string(
        "dashboard/vm-detail/_disk-operations.html",
        RequestContext(request, context),
    )

    return HttpResponse(
        json.dumps(response),
        content_type="application/json"
    )


class FavouriteView(TemplateView):

    def post(self, *args, **kwargs):
        user = self.request.user
        vm = Instance.objects.get(pk=self.request.POST.get("vm"))
        if not vm.has_level(user, 'user'):
            raise PermissionDenied()
        try:
            Favourite.objects.get(instance=vm, user=user).delete()
            return HttpResponse("Deleted.")
        except Favourite.DoesNotExist:
            Favourite(instance=vm, user=user).save()
            return HttpResponse("Added.")


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
                ugettext_noop('Ownership offer'),
                ugettext_noop('%(user)s offered you to take the ownership of '
                              'his/her virtual machine called %(instance)s. '
                              '<a href="%(token)s" '
                              'class="btn btn-success btn-small">Accept</a>'),
                {'instance': obj, 'token': token_path})
        except Profile.DoesNotExist:
            messages.error(request, _('Can not notify selected user.'))
        else:
            messages.success(request,
                             _('User %s is notified about the offer.') % (
                                 unicode(new_owner), ))

        return redirect(reverse_lazy("dashboard.views.detail",
                                     kwargs={'pk': obj.pk}))


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
                ugettext_noop('Ownership accepted'),
                ugettext_noop('Your ownership offer of %(instance)s has been '
                              'accepted by %(user)s.'),
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
    def get(self, request, pk, metric, time, *args, **kwargs):
        graphite_url = settings.GRAPHITE_URL
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
        logger.debug('%s %s', graphite_url, params)
        response = requests.get('%s/render/' % graphite_url, params=params)
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
        return 'circle.%s' % instance.host.hostname

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
        n = 10 if self.request.is_ajax() else 1000
        context['notifications'] = list(
            self.request.user.notification_set.all()[:n])
        return context

    def get(self, *args, **kwargs):
        response = super(NotificationView, self).get(*args, **kwargs)
        un = self.request.user.notification_set.filter(status="new")
        for u in un:
            u.status = "read"
            u.save()
        return response


def circle_login(request):
    authentication_form = CircleAuthenticationForm
    extra_context = {
        'saml2': saml_available,
    }
    response = login(request, authentication_form=authentication_form,
                     extra_context=extra_context)
    set_language_cookie(request, response)
    return response


class MyPreferencesView(UpdateView):
    model = Profile

    def get_context_data(self, *args, **kwargs):
        context = super(MyPreferencesView, self).get_context_data(*args,
                                                                  **kwargs)
        context['forms'] = {
            'change_password': CirclePasswordChangeForm(
                user=self.request.user),
            'change_language': MyProfileForm(instance=self.get_object()),
        }
        key_table = UserKeyListTable(
            UserKey.objects.filter(user=self.request.user),
            request=self.request)
        key_table.page = None
        context['userkey_table'] = key_table
        cmd_table = ConnectCommandListTable(
            self.request.user.command_set.all(),
            request=self.request)
        cmd_table.page = None
        context['connectcommand_table'] = cmd_table
        return context

    def get_object(self, queryset=None):
        if self.request.user.is_anonymous():
            raise PermissionDenied()
        try:
            return self.request.user.profile
        except Profile.DoesNotExist:
            raise Http404(_("You don't have a profile."))

    def post(self, request, *args, **kwargs):
        self.ojbect = self.get_object()
        redirect_response = HttpResponseRedirect(
            reverse("dashboard.views.profile-preferences"))
        if "preferred_language" in request.POST:
            form = MyProfileForm(request.POST, instance=self.get_object())
            if form.is_valid():
                lang = form.cleaned_data.get("preferred_language")
                set_language_cookie(self.request, redirect_response, lang)
                form.save()
        else:
            form = CirclePasswordChangeForm(user=request.user,
                                            data=request.POST)
            if form.is_valid():
                form.save()

        if form.is_valid():
            return redirect_response
        else:
            return self.get(request, form=form, *args, **kwargs)

    def get(self, request, form=None, *args, **kwargs):
        # if this is not here, it won't work
        self.object = self.get_object()
        context = self.get_context_data(*args, **kwargs)
        if form is not None:
            # a little cheating, users can't post invalid
            # language selection forms (without modifying the HTML)
            context['forms']['change_password'] = form
        return self.render_to_response(context)


class UnsubscribeFormView(SuccessMessageMixin, UpdateView):
    model = Profile
    form_class = UnsubscribeForm
    template_name = "dashboard/unsubscribe.html"
    success_message = _("Successfully modified subscription.")

    def get_success_url(self):
        if self.request.user.is_authenticated():
            return super(UnsubscribeFormView, self).get_success_url()
        else:
            return self.request.path

    @classmethod
    def get_salt(cls):
        return unicode(cls)

    @classmethod
    def get_token(cls, user):
        return signing.dumps(user.pk, salt=cls.get_salt(), compress=True)

    def get_object(self, queryset=None):
        key = self.kwargs['token']
        try:
            pk = signing.loads(key, salt=self.get_salt(), max_age=48 * 3600)
        except signing.SignatureExpired:
            raise
        except (signing.BadSignature, ValueError, TypeError) as e:
            logger.warning('Tried invalid token. Token: %s, user: %s. %s',
                           key, unicode(self.request.user), unicode(e))
            raise Http404
        else:
            return (queryset or self.get_queryset()).get(user_id=pk)

    def dispatch(self, request, *args, **kwargs):
        try:
            return super(UnsubscribeFormView, self).dispatch(
                request, *args, **kwargs)
        except signing.SignatureExpired:
            return redirect('dashboard.views.profile-preferences')


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
        app = disk.get_appliance()

        if not app.has_level(request.user, 'owner'):
            raise PermissionDenied()

        app.remove_disk(disk=disk, user=request.user)
        disk.destroy()

        next_url = request.POST.get("next")
        success_url = next_url if next_url else app.get_absolute_url()
        success_message = _("Disk successfully removed.")

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
    if not disk.get_appliance().has_level(request.user, 'owner'):
        raise PermissionDenied()

    return HttpResponse(
        json.dumps({
            'percentage': disk.get_download_percentage(),
            'failed': disk.failed
        }),
        content_type="application/json",
    )


def _get_activity_icon(act):
    op = act.get_operation()
    if op and op.id in vm_ops:
        return vm_ops[op.id].icon
    else:
        return "cog"


def _format_activities(acts):
    for i in acts:
        i.icon = _get_activity_icon(i)
    return acts


class InstanceActivityDetail(CheckedDetailView):
    model = InstanceActivity
    context_object_name = 'instanceactivity'  # much simpler to mock object
    template_name = 'dashboard/instanceactivity_detail.html'

    def get_has_level(self):
        return self.object.instance.has_level

    def get_context_data(self, **kwargs):
        ctx = super(InstanceActivityDetail, self).get_context_data(**kwargs)
        ctx['activities'] = _format_activities(
            self.object.instance.get_activities(self.request.user))
        ctx['icon'] = _get_activity_icon(self.object)
        return ctx


class UserCreationView(LoginRequiredMixin, PermissionRequiredMixin,
                       CreateView):
    form_class = UserCreationForm
    model = User
    template_name = 'dashboard/user-create.html'
    permission_required = "auth.add_user"

    def get_group(self, group_pk):
        self.group = get_object_or_404(Group, pk=group_pk)
        if not self.group.profile.has_level(self.request.user, 'owner'):
            raise PermissionDenied()

    def get(self, *args, **kwargs):
        self.get_group(kwargs.pop('group_pk'))
        return super(UserCreationView, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        group_pk = kwargs.pop('group_pk')
        self.get_group(group_pk)
        ret = super(UserCreationView, self).post(*args, **kwargs)
        if self.object:
            self.object.groups.add(self.group)
            return redirect(
                reverse('dashboard.views.group-detail', args=[group_pk]))
        else:
            return ret


class InterfaceDeleteView(DeleteView):
    model = Interface

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/confirm/ajax-delete.html']
        else:
            return ['dashboard/confirm/base-delete.html']

    def get_context_data(self, **kwargs):
        context = super(InterfaceDeleteView, self).get_context_data(**kwargs)
        interface = self.get_object()
        context['text'] = _("Are you sure you want to remove this interface "
                            "from <strong>%(vm)s</strong>?" %
                            {'vm': interface.instance.name})
        return context

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        instance = self.object.instance

        if not instance.has_level(request.user, "owner"):
            raise PermissionDenied()

        instance.remove_interface(interface=self.object, user=request.user)
        success_url = self.get_success_url()
        success_message = _("Interface successfully deleted.")

        if request.is_ajax():
            return HttpResponse(
                json.dumps(
                    {'message': success_message,
                     'removed_network': {
                         'vlan': self.object.vlan.name,
                         'vlan_pk': self.object.vlan.pk,
                         'managed': self.object.host is not None,
                     }}),
                content_type="application/json",
            )
        else:
            messages.success(request, success_message)
            return HttpResponseRedirect("%s#network" % success_url)

    def get_success_url(self):
        redirect = self.request.POST.get("next")
        if redirect:
            return redirect
        self.object.instance.get_absolute_url()


@require_GET
def get_vm_screenshot(request, pk):
    instance = get_object_or_404(Instance, pk=pk)
    try:
        image = instance.screenshot(user=request.user).getvalue()
    except:
        # TODO handle this better
        raise Http404()

    return HttpResponse(image, mimetype="image/png")


class ProfileView(LoginRequiredMixin, DetailView):
    template_name = "dashboard/profile.html"
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"

    def get_context_data(self, **kwargs):
        context = super(ProfileView, self).get_context_data(**kwargs)
        user = self.get_object()
        context['profile'] = user
        context['avatar_url'] = user.profile.get_avatar_url()
        context['instances_owned'] = Instance.get_objects_with_level(
            "owner", user, disregard_superuser=True).filter(destroyed_at=None)
        context['instances_with_access'] = Instance.get_objects_with_level(
            "user", user, disregard_superuser=True
        ).filter(destroyed_at=None).exclude(pk__in=context['instances_owned'])

        group_profiles = GroupProfile.get_objects_with_level(
            "operator", self.request.user)
        groups = Group.objects.filter(groupprofile__in=group_profiles)
        context['groups'] = user.groups.filter(pk__in=groups)

        # permissions
        # show groups only if the user is superuser, or have access
        # to any of the groups the user belongs to
        context['perm_group_list'] = (
            self.request.user.is_superuser or len(context['groups']) > 0)
        context['perm_email'] = (
            context['perm_group_list'] or self.request.user == user)

        # filter the virtual machine list
        # if the logged in user is not superuser or not the user itself
        # filter the list so only those virtual machines are shown that are
        # originated from templates the logged in user is operator or higher
        if not (self.request.user.is_superuser or self.request.user == user):
            it = InstanceTemplate.get_objects_with_level("operator",
                                                         self.request.user)
            context['instances_owned'] = context['instances_owned'].filter(
                template__in=it)
            context['instances_with_access'] = context[
                'instances_with_access'].filter(template__in=it)
        return context


@require_POST
def toggle_use_gravatar(request, **kwargs):
    user = get_object_or_404(User, username=kwargs['username'])
    if not request.user == user:
        raise PermissionDenied()

    profile = user.profile
    profile.use_gravatar = not profile.use_gravatar
    profile.save()

    new_avatar_url = user.profile.get_avatar_url()
    return HttpResponse(
        json.dumps({'new_avatar_url': new_avatar_url}),
        content_type="application/json",
    )


class UserKeyDetail(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = UserKey
    template_name = "dashboard/userkey-edit.html"
    form_class = UserKeyForm
    success_message = _("Successfully modified SSH key.")

    def get(self, request, *args, **kwargs):
        object = self.get_object()
        if object.user != request.user:
            raise PermissionDenied()
        return super(UserKeyDetail, self).get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("dashboard.views.userkey-detail",
                            kwargs=self.kwargs)

    def post(self, request, *args, **kwargs):
        object = self.get_object()
        if object.user != request.user:
            raise PermissionDenied()
        return super(UserKeyDetail, self).post(self, request, args, kwargs)


class UserKeyDelete(LoginRequiredMixin, DeleteView):
    model = UserKey

    def get_success_url(self):
        return reverse("dashboard.views.profile-preferences")

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/confirm/ajax-delete.html']
        else:
            return ['dashboard/confirm/base-delete.html']

    def delete(self, request, *args, **kwargs):
        object = self.get_object()
        if object.user != request.user:
            raise PermissionDenied()

        object.delete()
        success_url = self.get_success_url()
        success_message = _("SSH key successfully deleted.")

        if request.is_ajax():
            return HttpResponse(
                json.dumps({'message': success_message}),
                content_type="application/json",
            )
        else:
            messages.success(request, success_message)
            return HttpResponseRedirect(success_url)


class UserKeyCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = UserKey
    form_class = UserKeyForm
    template_name = "dashboard/userkey-create.html"
    success_message = _("Successfully created a new SSH key.")

    def get_success_url(self):
        return reverse_lazy("dashboard.views.profile-preferences")

    def get_form_kwargs(self):
        kwargs = super(UserKeyCreate, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class ConnectCommandDetail(LoginRequiredMixin, SuccessMessageMixin,
                           UpdateView):
    model = ConnectCommand
    template_name = "dashboard/connect-command-edit.html"
    form_class = ConnectCommandForm
    success_message = _("Successfully modified command template.")

    def get(self, request, *args, **kwargs):
        object = self.get_object()
        if object.user != request.user:
            raise PermissionDenied()
        return super(ConnectCommandDetail, self).get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("dashboard.views.connect-command-detail",
                            kwargs=self.kwargs)

    def post(self, request, *args, **kwargs):
        object = self.get_object()
        if object.user != request.user:
            raise PermissionDenied()
        return super(ConnectCommandDetail, self).post(request, args, kwargs)

    def get_form_kwargs(self):
        kwargs = super(ConnectCommandDetail, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class ConnectCommandDelete(LoginRequiredMixin, DeleteView):
    model = ConnectCommand

    def get_success_url(self):
        return reverse("dashboard.views.profile-preferences")

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/confirm/ajax-delete.html']
        else:
            return ['dashboard/confirm/base-delete.html']

    def delete(self, request, *args, **kwargs):
        object = self.get_object()
        if object.user != request.user:
            raise PermissionDenied()

        object.delete()
        success_url = self.get_success_url()
        success_message = _("Command template successfully deleted.")

        if request.is_ajax():
            return HttpResponse(
                json.dumps({'message': success_message}),
                content_type="application/json",
            )
        else:
            messages.success(request, success_message)
            return HttpResponseRedirect(success_url)


class ConnectCommandCreate(LoginRequiredMixin, SuccessMessageMixin,
                           CreateView):
    model = ConnectCommand
    form_class = ConnectCommandForm
    template_name = "dashboard/connect-command-create.html"
    success_message = _("Successfully created a new command template.")

    def get_success_url(self):
        return reverse_lazy("dashboard.views.profile-preferences")

    def get_form_kwargs(self):
        kwargs = super(ConnectCommandCreate, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class HelpView(TemplateView):

    def get_context_data(self, *args, **kwargs):
        ctx = super(HelpView, self).get_context_data(*args, **kwargs)
        ctx.update({"saml": hasattr(settings, "SAML_CONFIG"),
                    "store": settings.STORE_URL})
        return ctx


class StoreList(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/store/list.html"

    def get_context_data(self, **kwargs):
        context = super(StoreList, self).get_context_data(**kwargs)
        directory = self.request.GET.get("directory", "/")
        directory = "/" if not len(directory) else directory

        store = Store(self.request.user)
        context['root'] = store.list(directory)
        context['quota'] = store.get_quota()
        context['up_url'] = self.create_up_directory(directory)
        context['current'] = directory
        context['next_url'] = "%s%s?directory=%s" % (
            settings.DJANGO_URL.rstrip("/"),
            reverse("dashboard.views.store-list"), directory)
        return context

    def get(self, *args, **kwargs):
        try:
            if self.request.is_ajax():
                context = self.get_context_data(**kwargs)
                return render_to_response(
                    "dashboard/store/_list-box.html",
                    RequestContext(self.request, context),
                )
            else:
                return super(StoreList, self).get(*args, **kwargs)
        except NoStoreException:
            messages.warning(self.request, _("No store."))
        except NotOkException:
            messages.warning(self.request, _("Store has some problems now."
                                             " Try again later."))
        except Exception as e:
            logger.critical("Something is wrong with store: %s", unicode(e))
            messages.warning(self.request, _("Unknown store error."))
        return redirect("/")

    def create_up_directory(self, directory):
        path = normpath(join('/', directory, '..'))
        if not path.endswith("/"):
            path += "/"
        return path


@require_GET
@login_required
def store_download(request):
    path = request.GET.get("path")
    try:
        url = Store(request.user).request_download(path)
    except Exception:
        messages.error(request, _("Something went wrong during download."))
        logger.exception("Unable to download, "
                         "maybe it is already deleted")
        return redirect(reverse("dashboard.views.store-list"))
    return redirect(url)


@require_GET
@login_required
def store_upload(request):
    directory = request.GET.get("directory", "/")
    try:
        action = Store(request.user).request_upload(directory)
    except Exception:
        logger.exception("Unable to upload")
        messages.error(request, _("Unable to upload file."))
        return redirect("/")

    next_url = "%s%s?directory=%s" % (
        settings.DJANGO_URL.rstrip("/"),
        reverse("dashboard.views.store-list"), directory)

    return render(request, "dashboard/store/upload.html",
                  {'directory': directory, 'action': action,
                   'next_url': next_url})


@require_GET
@login_required
def store_get_upload_url(request):
    current_dir = request.GET.get("current_dir")
    try:
        url = Store(request.user).request_upload(current_dir)
    except Exception:
        logger.exception("Unable to upload")
        messages.error(request, _("Unable to upload file."))
        return redirect("/")
    return HttpResponse(
        json.dumps({'url': url}), content_type="application/json")


class StoreRemove(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/store/remove.html"

    def get_context_data(self, *args, **kwargs):
        context = super(StoreRemove, self).get_context_data(*args, **kwargs)
        path = self.request.GET.get("path", "/")
        if path == "/":
            SuspiciousOperation()

        context['path'] = path
        context['is_dir'] = path.endswith("/")
        if context['is_dir']:
            context['directory'] = path
        else:
            context['directory'] = dirname(path)
            context['name'] = basename(path)

        return context

    def get(self, *args, **kwargs):
        try:
            return super(StoreRemove, self).get(*args, **kwargs)
        except NoStoreException:
            return redirect("/")

    def post(self, *args, **kwargs):
        path = self.request.POST.get("path")
        try:
            Store(self.request.user).remove(path)
        except Exception:
            logger.exception("Unable to remove %s", path)
            messages.error(self.request, _("Unable to remove %s.") % path)

        return redirect("%s?directory=%s" % (
            reverse("dashboard.views.store-list"),
            dirname(dirname(path)),
        ))


@require_POST
@login_required
def store_new_directory(request):
    path = request.POST.get("path")
    name = request.POST.get("name")

    try:
        Store(request.user).new_folder(join(path, name))
    except Exception:
        logger.exception("Unable to create folder %s in %s for %s",
                         name, path, unicode(request.user))
        messages.error(request, _("Unable to create folder."))
    return redirect("%s?directory=%s" % (
        reverse("dashboard.views.store-list"), path))


@require_POST
@login_required
def store_refresh_toplist(request):
    cache_key = "files-%d" % request.user.pk
    cache = get_cache("default")
    try:
        store = Store(request.user)
        toplist = store.toplist()
        quota = store.get_quota()
        files = {'toplist': toplist, 'quota': quota}
    except Exception:
        logger.exception("Can't get toplist of %s", unicode(request.user))
        files = {'toplist': []}
    cache.set(cache_key, files, 300)

    return redirect(reverse("dashboard.index"))


def absolute_url(url):
    return urljoin(settings.DJANGO_URL, url)
