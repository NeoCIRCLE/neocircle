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

import json
import logging
from collections import OrderedDict
from os import getenv

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import (
    HttpResponse, Http404, HttpResponseRedirect, JsonResponse
)
from django.shortcuts import redirect, get_object_or_404
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.translation import (
    ugettext as _, ugettext_noop, ungettext_lazy,
)
from django.views.decorators.http import require_GET
from django.views.generic import (
    UpdateView, ListView, TemplateView
)

from braces.views import SuperuserRequiredMixin, LoginRequiredMixin

from common.models import (
    create_readable, HumanReadableException, fetch_human_exception,
)
from firewall.models import Vlan, Host, Rule
from manager.scheduler import SchedulerError
from storage.models import Disk
from vm.models import (
    Instance, InstanceActivity, Node, Lease,
    InstanceTemplate, InterfaceTemplate, Interface,
)
from .util import (
    CheckedDetailView, AjaxOperationMixin, OperationView, AclUpdateView,
    FormOperationMixin, FilterMixin, GraphMixin,
    TransferOwnershipConfirmView, TransferOwnershipView,
)
from ..forms import (
    AclUserOrGroupAddForm, VmResourcesForm, TraitsForm, RawDataForm,
    ToggleBootMenuForm,
    VmAddInterfaceForm, VmCreateDiskForm, VmDownloadDiskForm, VmSaveForm,
    VmRenewForm, VmStateChangeForm, VmListSearchForm, VmCustomizeForm,
    VmDiskResizeForm, RedeployForm, VmDiskRemoveForm,
    VmMigrateForm, VmDeployForm,
    VmPortRemoveForm, VmPortAddForm,
    VmRemoveInterfaceForm,
)
from request.models import TemplateAccessType, LeaseType
from request.forms import LeaseRequestForm, TemplateRequestForm
from ..models import Favourite
from manager.scheduler import has_traits

logger = logging.getLogger(__name__)


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
            with self.object.activity(
                    code_suffix='console-accessed', user=request.user,
                    readable_name=ugettext_noop("console access"),
                    concurrency_check=False):
                port = self.object.vnc_port
                host = str(self.object.node.host.ipv4)
                value = signing.dumps({'host': host, 'port': port},
                                      key=getenv("PROXY_SECRET", 'asdasd')),
                return HttpResponse('vnc/?d=%s' % value)
        else:
            raise Http404()


class VmDetailView(GraphMixin, CheckedDetailView):
    template_name = "dashboard/vm-detail.html"
    model = Instance

    def get(self, *args, **kwargs):
        if self.request.is_ajax():
            return JsonResponse(self.get_json_data())
        else:
            return super(VmDetailView, self).get(*args, **kwargs)

    def get_json_data(self):
        instance = self.get_object()
        return {"status": instance.status,
                "host": instance.get_connect_host(),
                "port": instance.get_connect_port(),
                "password": instance.pw}

    def get_context_data(self, **kwargs):
        context = super(VmDetailView, self).get_context_data(**kwargs)
        instance = context['instance']
        user = self.request.user
        is_operator = instance.has_level(user, "operator")
        is_owner = instance.has_level(user, "owner")
        ops = get_operations(instance, user)
        hide_tutorial = self.request.COOKIES.get(
            "hide_tutorial_for_%s" % instance.pk) == "True"
        context.update({
            'graphite_enabled': settings.GRAPHITE_URL is not None,
            'vnc_url': reverse_lazy("dashboard.views.detail-vnc",
                                    kwargs={'pk': self.object.pk}),
            'ops': ops,
            'op': {i.op: i for i in ops},
            'connect_commands': user.profile.get_connect_commands(instance),
            'hide_tutorial': hide_tutorial,
            'fav': instance.favourite_set.filter(user=user).exists(),
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
        context['aclform'] = AclUserOrGroupAddForm()
        context['os_type_icon'] = instance.os_type.replace("unknown",
                                                           "question")
        # ipv6 infos
        context['ipv6_host'] = instance.get_connect_host(use_ipv6=True)
        context['ipv6_port'] = instance.get_connect_port(use_ipv6=True)

        # resources forms
        can_edit = (
            instance.has_level(user, "owner") and
            self.request.user.has_perm("vm.change_resources"))
        context['resources_form'] = VmResourcesForm(
            can_edit=can_edit, instance=instance)

        if self.request.user.is_superuser:
            context['traits_form'] = TraitsForm(instance=instance)
            context['raw_data_form'] = RawDataForm(instance=instance)

        if is_owner and user.has_perm("vm.toggle_boot_menu"):
            context['toggle_boot_menu_form'] =\
                ToggleBootMenuForm(instance=instance)

        # resources change perm
        context['can_change_resources'] = self.request.user.has_perm(
            "vm.change_resources")

        # client info
        context['client_download'] = self.request.COOKIES.get(
            'downloaded_client')
        # can link template
        context['can_link_template'] = instance.template and is_operator

        # is operator/owner
        context['is_operator'] = is_operator
        context['is_owner'] = is_owner

        # operation also allows RUNNING (if with_shutdown is present)
        context['save_resources_enabled'] = instance.status in (
            "STOPPED",
            "PENDING",
        )

        return context

    def post(self, request, *args, **kwargs):
        options = {
            'new_name': self.__set_name,
            'new_description': self.__set_description,
            'new_tag': self.__add_tag,
            'to_remove': self.__remove_tag,
            'abort_operation': self.__abort_operation,
        }
        for k, v in options.iteritems():
            if request.POST.get(k) is not None:
                return v(request)
        raise Http404()

    def __set_name(self, request):
        self.object = self.get_object()
        if not self.object.has_level(request.user, "operator"):
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
        if not self.object.has_level(request.user, "operator"):
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
        if not self.object.has_level(request.user, "operator"):
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
            if not self.object.has_level(request.user, "operator"):
                raise PermissionDenied()

            self.object.tags.remove(to_remove)
            message = u"Success"
        except:  # note this won't really happen
            message = u"Not success"

        if request.is_ajax():
            return JsonResponse({'message': message})
        else:
            return redirect(reverse_lazy("dashboard.views.detail",
                            kwargs={'pk': self.object.pk}))

    def __abort_operation(self, request):
        self.object = self.get_object()

        activity = get_object_or_404(InstanceActivity,
                                     pk=request.POST.get("activity"))
        if not activity.is_abortable_for(request.user):
            raise PermissionDenied()
        activity.abort()
        return HttpResponseRedirect("%s#activity" %
                                    self.object.get_absolute_url())


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


class VmToggleBootMenuUpdate(LoginRequiredMixin, UpdateView):
    form_class = ToggleBootMenuForm
    model = Instance

    def get(self, *args, **kwargs):
        raise Http404()

    def form_valid(self, form):
        user = self.request.user
        is_owner = form.instance.has_level(user, "owner")

        if not (is_owner and user.has_perm("vm.toggle_boot_menu")):
            raise PermissionDenied()

        return super(VmToggleBootMenuUpdate, self).form_valid(form)

    def get_success_url(self):
        return self.get_object().get_absolute_url() + "#resources"


class VmOperationView(AjaxOperationMixin, OperationView):

    model = Instance
    context_object_name = 'instance'  # much simpler to mock object


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


class VmRemoveInterfaceView(FormOperationMixin, VmOperationView):
    op = 'remove_interface'
    form_class = VmRemoveInterfaceForm
    show_in_toolbar = False
    wait_for_result = 0.5
    icon = 'times'
    effect = "danger"
    with_reload = True

    def get_form_kwargs(self):
        instance = self.get_op().instance
        choices = instance.interface_set.all()
        interface_pk = self.request.GET.get('interface')
        if interface_pk:
            try:
                default = choices.get(pk=interface_pk)
            except (ValueError, Interface.DoesNotExist):
                raise Http404()
        else:
            default = None

        val = super(VmRemoveInterfaceView, self).get_form_kwargs()
        val.update({'choices': choices, 'default': default})
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


class VmDiskModifyView(FormOperationMixin, VmOperationView):
    show_in_toolbar = False
    with_reload = True
    icon = 'arrows-alt'
    effect = "success"

    def get_form_kwargs(self):
        choices = self.get_op().instance.disks
        disk_pk = self.request.GET.get('disk')
        if disk_pk:
            try:
                default = choices.get(pk=disk_pk)
            except (ValueError, Disk.DoesNotExist):
                raise Http404()
        else:
            default = None

        val = super(VmDiskModifyView, self).get_form_kwargs()
        val.update({'choices': choices, 'default': default})
        return val


class VmCreateDiskView(FormOperationMixin, VmOperationView):

    op = 'create_disk'
    form_class = VmCreateDiskForm
    show_in_toolbar = False
    icon = 'hdd-o'
    effect = "success"
    is_disk_operation = True
    with_reload = True

    def get_form_kwargs(self):
        op = self.get_op()
        val = super(VmCreateDiskView, self).get_form_kwargs()
        num = op.instance.disks.count() + 1
        val['default'] = "%s %d" % (op.instance.name, num)
        return val


class VmDownloadDiskView(FormOperationMixin, VmOperationView):

    op = 'download_disk'
    form_class = VmDownloadDiskForm
    show_in_toolbar = False
    icon = 'download'
    effect = "success"
    is_disk_operation = True
    with_reload = True


class VmMigrateView(FormOperationMixin, VmOperationView):

    op = 'migrate'
    icon = 'truck'
    effect = 'info'
    template_name = 'dashboard/_vm-migrate.html'
    form_class = VmMigrateForm

    def get_form_kwargs(self):
        online = (n.pk for n in Node.objects.filter(enabled=True) if n.online)
        choices = Node.objects.filter(pk__in=online)
        default = None
        inst = self.get_object()
        try:
            if isinstance(inst, Instance):
                default = inst.select_node()
        except SchedulerError:
            logger.exception("scheduler error:")

        val = super(VmMigrateView, self).get_form_kwargs()
        val.update({'choices': choices, 'default': default})
        return val

    def get_context_data(self, *args, **kwargs):
        ctx = super(VmMigrateView, self).get_context_data(*args, **kwargs)

        inst = self.get_object()
        if isinstance(inst, Instance):
            nodes_w_traits = [
                n.pk for n in Node.objects.filter(enabled=True)
                if n.online and
                has_traits(inst.req_traits.all(), n)
            ]
            ctx['nodes_w_traits'] = nodes_w_traits

        return ctx


class VmPortRemoveView(FormOperationMixin, VmOperationView):

    template_name = 'dashboard/_vm-remove-port.html'
    op = 'remove_port'
    show_in_toolbar = False
    with_reload = True
    wait_for_result = 0.5
    icon = 'times'
    effect = "danger"
    form_class = VmPortRemoveForm

    def get_form_kwargs(self):
        instance = self.get_op().instance
        choices = Rule.portforwards().filter(
            host__interface__instance=instance)
        rule_pk = self.request.GET.get('rule')
        if rule_pk:
            try:
                default = choices.get(pk=rule_pk)
            except (ValueError, Rule.DoesNotExist):
                raise Http404()
        else:
            default = None

        val = super(VmPortRemoveView, self).get_form_kwargs()
        val.update({'choices': choices, 'default': default})
        return val


class VmPortAddView(FormOperationMixin, VmOperationView):

    op = 'add_port'
    show_in_toolbar = False
    with_reload = True
    wait_for_result = 0.5
    icon = 'plus'
    effect = "success"
    form_class = VmPortAddForm

    def get_form_kwargs(self):
        instance = self.get_op().instance
        choices = Host.objects.filter(interface__instance=instance)
        host_pk = self.request.GET.get('host')
        if host_pk:
            try:
                default = choices.get(pk=host_pk)
            except (ValueError, Host.DoesNotExist):
                raise Http404()
        else:
            default = None

        val = super(VmPortAddView, self).get_form_kwargs()
        val.update({'choices': choices, 'default': default})
        return val


class VmSaveView(FormOperationMixin, VmOperationView):

    op = 'save_as_template'
    icon = 'save'
    effect = 'info'
    form_class = VmSaveForm

    def get_form_kwargs(self):
        op = self.get_op()
        val = super(VmSaveView, self).get_form_kwargs()
        val['default'] = op._rename(op.instance.name)
        obj = self.get_object()
        if obj.template and obj.template.has_level(
                self.request.user, "owner"):
            val['clone'] = True
        return val


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
                return JsonResponse({'success': False,
                                     'messages': [unicode(m) for m in store]})
            else:
                return HttpResponseRedirect(instance.get_absolute_url() +
                                            "#resources")
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
    effect = 'success'
    show_in_toolbar = False
    form_class = VmRenewForm
    wait_for_result = 0.5
    template_name = 'dashboard/_vm-renew.html'
    with_reload = True

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

    def get_context_data(self, **kwargs):
        context = super(VmRenewView, self).get_context_data(**kwargs)
        context['lease_request_form'] = LeaseRequestForm(request=self.request)
        context['lease_types'] = LeaseType.objects.exists()
        return context


class VmStateChangeView(FormOperationMixin, VmOperationView):
    op = 'emergency_change_state'
    icon = 'legal'
    effect = 'danger'
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


class RedeployView(FormOperationMixin, VmOperationView):
    op = 'redeploy'
    icon = 'stethoscope'
    effect = 'danger'
    show_in_toolbar = True
    form_class = RedeployForm
    wait_for_result = 0.5


class VmDeployView(FormOperationMixin, VmOperationView):
    op = 'deploy'
    icon = 'play'
    effect = 'success'
    form_class = VmDeployForm

    def get_form_kwargs(self):
        kwargs = super(VmDeployView, self).get_form_kwargs()
        if self.request.user.is_superuser:
            online = (n.pk for n in
                      Node.objects.filter(enabled=True) if n.online)
            kwargs['choices'] = Node.objects.filter(pk__in=online)
            kwargs['instance'] = self.get_object()
        return kwargs


vm_ops = OrderedDict([
    ('deploy', VmDeployView),
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
        op='shut_off', icon='plug', effect='warning')),
    ('recover', VmOperationView.factory(
        op='recover', icon='medkit', effect='warning')),
    ('nostate', VmStateChangeView),
    ('redeploy', RedeployView),
    ('destroy', VmOperationView.factory(
        extra_bases=[TokenOperationView],
        op='destroy', icon='times', effect='danger')),
    ('create_disk', VmCreateDiskView),
    ('download_disk', VmDownloadDiskView),
    ('resize_disk', VmDiskModifyView.factory(
        op='resize_disk', form_class=VmDiskResizeForm,
        icon='arrows-alt', effect="warning")),
    ('remove_disk', VmDiskModifyView.factory(
        op='remove_disk', form_class=VmDiskRemoveForm,
        icon='times', effect="danger")),
    ('add_interface', VmAddInterfaceView),
    ('remove_interface', VmRemoveInterfaceView),
    ('remove_port', VmPortRemoveView),
    ('add_port', VmPortAddView),
    ('renew', VmRenewView),
    ('resources_change', VmResourcesChangeView),
    ('password_reset', VmOperationView.factory(
        op='password_reset', icon='unlock', effect='warning',
        show_in_toolbar=False, wait_for_result=0.5, with_reload=True)),
    ('mount_store', VmOperationView.factory(
        op='mount_store', icon='briefcase', effect='info',
        show_in_toolbar=False,
    )),
    ('install_keys', VmOperationView.factory(
        op='install_keys', icon='key', effect='info',
        show_in_toolbar=False,
    )),
])


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

        if hasattr(self, 'form_class'):
            form = self.form_class(self.request.POST, **self.get_form_kwargs())
            if form.is_valid():
                extra.update(form.cleaned_data)

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


class VmList(LoginRequiredMixin, FilterMixin, ListView):
    template_name = "dashboard/vm-list.html"
    allowed_filters = {
        'name': "name__icontains",
        'node': "node__name__icontains",
        'node_exact': "node__name",
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
        context['show_acts_in_progress'] = self.object_list.count() < 100
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
                'url': reverse('dashboard.views.detail', args=[i.pk]),
                'name': i.name,
                'icon': i.get_status_icon(),
                'host': i.short_hostname,
                'status': i.get_status_display(),
                'owner': (i.owner.profile.get_display_name()
                          if i.owner != self.request.user else None),
                'fav': i.pk in favs,
            } for i in instances]
            return HttpResponse(
                json.dumps(list(instances)),  # instances is ValuesQuerySet
                content_type="application/json",
            )

    def create_acl_queryset(self, model):
        queryset = super(VmList, self).create_acl_queryset(model)
        if not self.search_form.cleaned_data.get("include_deleted"):
            queryset = queryset.filter(destroyed_at=None)
        return queryset

    def get_queryset(self):
        logger.debug('VmList.get_queryset() called. User: %s',
                     unicode(self.request.user))
        queryset = self.create_acl_queryset(Instance)

        self.create_fake_get()
        sort = self.request.GET.get("sort")
        # remove "-" that means descending order
        # also check if the column name is valid
        if (sort and
            (sort[1:] if sort[0] == "-" else sort)
                in [i.name for i in Instance._meta.fields] + ["pk"]):
            queryset = queryset.order_by(sort)

        filters, excludes = self.get_queryset_filters()
        return queryset.filter(**filters).exclude(**excludes).prefetch_related(
            "owner", "node", "owner__profile", "interface_set", "lease",
            "interface_set__host").distinct()


class VmCreate(LoginRequiredMixin, TemplateView):

    form_class = VmCustomizeForm
    form = None

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/_modal.html']
        else:
            return ['dashboard/nojs-wrapper.html']

    def get_template(self, request, pk):
        try:
            template = InstanceTemplate.objects.get(
                pk=int(pk))
        except (ValueError, InstanceTemplate.DoesNotExist):
            raise Http404()
        if not template.has_level(request.user, 'user'):
            raise PermissionDenied()

        return template

    def get(self, request, form=None, *args, **kwargs):
        if not request.user.has_perm('vm.create_vm'):
            raise PermissionDenied()

        if form is None:
            template_pk = request.GET.get("template")
        else:
            template_pk = form.template.pk

        if template_pk:
            template = self.get_template(request, template_pk)
            if form is None:
                form = self.form_class(user=request.user, template=template)
        else:
            templates = InstanceTemplate.get_objects_with_level(
                'user', request.user, disregard_superuser=True)

        context = self.get_context_data(**kwargs)
        if template_pk:
            context.update({
                'template': 'dashboard/_vm-create-2.html',
                'box_title': _('Customize VM'),
                'ajax_title': True,
                'vm_create_form': form,
                'template_o': template,
            })
        else:
            context.update({
                'template': 'dashboard/_vm-create-1.html',
                'box_title': _('Create a VM'),
                'ajax_title': True,
                'templates': templates.all(),
                'template_access_types': TemplateAccessType.objects.exists(),
                'form': TemplateRequestForm(request=request),
            })
        return self.render_to_response(context)

    def __create_normal(self, request, template, *args, **kwargs):
        instances = [Instance.create_from_template(
            template=template,
            owner=request.user)]
        return self.__deploy(request, instances)

    def __create_customized(self, request, template, *args, **kwargs):
        user = request.user
        # no form yet, using POST directly:
        form = self.form_class(
            request.POST, user=request.user, template=template)
        if not form.is_valid():
            return self.get(request, form, *args, **kwargs)
        post = form.cleaned_data

        ikwargs = {
            'name': post['name'],
            'template': template,
            'owner': user,
        }
        amount = post.get("amount", 1)
        if request.user.has_perm('vm.set_resources'):
            networks = [InterfaceTemplate(vlan=l, managed=l.managed)
                        for l in post['networks']]

            ikwargs.update({
                'num_cores': post['cpu_count'],
                'ram_size': post['ram_size'],
                'priority': post['cpu_priority'],
                'max_ram_size': post['ram_size'],
                'networks': networks,
                'disks': list(template.disks.all()),
            })

        else:
            pass

        instances = Instance.mass_create_from_template(amount=amount,
                                                       **ikwargs)
        return self.__deploy(request, instances)

    def __deploy(self, request, instances, *args, **kwargs):
        # workaround EncodeError: dictionary changed size during iteration
        user = User.objects.get(pk=request.user.pk)
        for i in instances:
            i.deploy.async(user=user)

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
            return HttpResponseRedirect("%s#activity" % path)

    def post(self, request, *args, **kwargs):
        user = request.user

        if not request.user.has_perm('vm.create_vm'):
            raise PermissionDenied()

        template = self.get_template(request, request.POST.get("template"))

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

        return create_func(request, template, *args, **kwargs)


@require_GET
def get_vm_screenshot(request, pk):
    instance = get_object_or_404(Instance, pk=pk)
    try:
        image = instance.screenshot(user=request.user).getvalue()
    except:
        # TODO handle this better
        raise Http404()

    return HttpResponse(image, content_type="image/png")


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


class ClientCheck(LoginRequiredMixin, TemplateView):

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/_modal.html']
        else:
            return ['dashboard/nojs-wrapper.html']

    def get_context_data(self, *args, **kwargs):
        context = super(ClientCheck, self).get_context_data(*args, **kwargs)
        context.update({
            'box_title': _('About CIRCLE Client'),
            'ajax_title': False,
            'client_download_url': settings.CLIENT_DOWNLOAD_URL,
            'template': "dashboard/_client-check.html",
            'instance': get_object_or_404(
                Instance, pk=self.request.GET.get('vm')),
        })
        if not context['instance'].has_level(self.request.user, 'user'):
            raise PermissionDenied()
        return context

    def post(self, request, *args, **kwargs):
        instance = get_object_or_404(Instance, pk=request.POST.get('vm'))
        if not instance.has_level(request.user, 'operator'):
            raise PermissionDenied()
        response = redirect(instance.get_absolute_url())
        response.set_cookie('downloaded_client', 'True', 365 * 24 * 60 * 60)
        return response


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

    response['connect_uri'] = instance.get_connect_uri()
    response['human_readable_status'] = instance.get_status_display()
    response['status'] = instance.status
    response['icon'] = instance.get_status_icon()
    latest = instance.get_latest_activity_in_progress()
    response['is_new_state'] = (latest and
                                latest.resultant_state is not None and
                                instance.status != latest.resultant_state)

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


class TransferInstanceOwnershipConfirmView(TransferOwnershipConfirmView):
    template = "dashboard/confirm/transfer-instance-ownership.html"
    model = Instance

    def change_owner(self, instance, new_owner):
        with instance.activity(
            code_suffix='ownership-transferred',
                readable_name=ugettext_noop("transfer ownership"),
                concurrency_check=False, user=new_owner):
            super(TransferInstanceOwnershipConfirmView, self).change_owner(
                instance, new_owner)


class TransferInstanceOwnershipView(TransferOwnershipView):
    confirm_view = TransferInstanceOwnershipConfirmView
    model = Instance
    notification_msg = ugettext_noop(
        '%(owner)s offered you to take the ownership of '
        'his/her virtual machine called %(instance)s. '
        '<a href="%(token)s" '
        'class="btn btn-success btn-small">Accept</a>')
    token_url = 'dashboard.views.vm-transfer-ownership-confirm'
    template = "dashboard/vm-detail/tx-owner.html"


@login_required
def toggle_template_tutorial(request, pk):
    hidden = request.POST.get("hidden", "").lower() == "true"
    instance = get_object_or_404(Instance, pk=pk)
    response = HttpResponseRedirect(instance.get_absolute_url())
    response.set_cookie(  # for a week
        "hide_tutorial_for_%s" % pk, hidden, 7 * 24 * 60 * 60)
    return response
