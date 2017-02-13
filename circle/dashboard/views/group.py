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
from itertools import chain

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import HttpResponse, Http404
from django.shortcuts import redirect
from django.utils.translation import ugettext as _
from django.views.generic import UpdateView, TemplateView

from braces.views import SuperuserRequiredMixin, LoginRequiredMixin
from django_tables2 import SingleTableView

from ..forms import (
    AddGroupMemberForm, AclUserOrGroupAddForm, GroupPermissionForm,
    GroupCreateForm, GroupProfileUpdateForm,
)
from ..models import FutureMember, GroupProfile
from vm.models import Instance, InstanceTemplate
from ..tables import GroupListTable
from .util import (CheckedDetailView, AclUpdateView, search_user,
                   saml_available, DeleteViewBase, external_auth_available)

logger = logging.getLogger(__name__)


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
                                 identity_cache=IdentityCache(request.session))
            subject_id = _get_subject_id(request.session)
            if not subject_id:
                return newgroups
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
        context['aclform'] = AclUserOrGroupAddForm()
        context['addmemberform'] = AddGroupMemberForm()
        context['group_profile_form'] = GroupProfileUpdate.get_form_object(
            self.request, self.object.profile)

        context.update({
            'group_objects': GroupProfile.get_objects_with_group_level(
                "operator", self.get_object()),
            'vm_objects': Instance.get_objects_with_group_level(
                "user", self.get_object()),
            'template_objects': InstanceTemplate.get_objects_with_group_level(
                "user", self.get_object()),
        })

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
        if request.POST.get('new_member'):
            return self.__add_user(request)
        if request.POST.get('new_members'):
            return self.__add_list(request)
        return redirect(reverse_lazy("dashboard.views.group-detail",
                                     kwargs={'pk': self.get_object().pk}))

    def __add_user(self, request):
        name = request.POST['new_member']
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
            if external_auth_available():
                FutureMember.objects.get_or_create(org_id=name.upper(),
                                                   group=self.object)
            else:
                messages.warning(request, _('User "%s" not found.') % name)

    def __add_list(self, request):
        userlist = request.POST.get('new_members').split('\r\n')
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


class GroupAclUpdateView(AclUpdateView):
    model = GroupProfile


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


class GroupRemoveUserView(DeleteViewBase):
    model = Group
    slug_field = 'pk'
    slug_url_kwarg = 'group_pk'
    level = 'operator'
    member_key = 'member_pk'
    success_message = _("Member successfully removed from group.")

    def check_auth(self):
        if not self.get_object().profile.has_level(
                self.request.user, self.level):
            raise PermissionDenied()

    def get_context_data(self, **kwargs):
        context = super(GroupRemoveUserView, self).get_context_data(**kwargs)
        try:
            context['member'] = User.objects.get(pk=self.member_pk)
        except User.DoesNotExist:
            raise Http404()
        return context

    def get_success_url(self):
        return reverse_lazy("dashboard.views.group-detail",
                            kwargs={'pk': self.get_object().pk})

    def get(self, request, member_pk, *args, **kwargs):
        self.member_pk = member_pk
        return super(GroupRemoveUserView, self).get(request, *args, **kwargs)

    def remove_member(self, pk):
        container = self.get_object()
        container.user_set.remove(User.objects.get(pk=pk))

    def delete_obj(self, request, *args, **kwargs):
        self.remove_member(kwargs[self.member_key])


class GroupRemoveFutureUserView(GroupRemoveUserView):
    member_key = 'member_org_id'
    success_message = _("Future user successfully removed from group.")

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


class GroupDelete(DeleteViewBase):
    model = Group
    success_message = _("Group successfully deleted.")

    def check_auth(self):
        if not self.get_object().profile.has_level(self.request.user, 'owner'):
            raise PermissionDenied()

    def get_success_url(self):
        return reverse_lazy('dashboard.views.group-list')


class GroupCreate(GroupCodeMixin, LoginRequiredMixin, TemplateView):

    form_class = GroupCreateForm

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/_modal.html']
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
