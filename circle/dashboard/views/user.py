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

import pyotp

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User, Group
from django.contrib.messages.views import SuccessMessageMixin
from django.core import signing
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.core.urlresolvers import reverse, reverse_lazy
from django.core.paginator import Paginator, InvalidPage
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import redirect, get_object_or_404
from django.templatetags.static import static
from django.utils.translation import ugettext as _
from django.views.decorators.http import require_POST
from django.views.generic import (
    TemplateView, View, UpdateView, CreateView, FormView
)
from django_sshkey.models import UserKey

from braces.views import LoginRequiredMixin, PermissionRequiredMixin

from django_tables2 import SingleTableView

from vm.models import Instance, InstanceTemplate

from ..forms import (
    CircleAuthenticationForm, MyProfileForm, UserCreationForm, UnsubscribeForm,
    UserKeyForm, CirclePasswordChangeForm, ConnectCommandForm,
    UserListSearchForm, UserEditForm, TwoFactorForm, TwoFactorConfirmationForm,
)
from ..models import Profile, GroupProfile, ConnectCommand
from ..tables import (
    UserKeyListTable, ConnectCommandListTable, UserListTable,
)

from .util import saml_available, DeleteViewBase, LoginView


logger = logging.getLogger(__name__)


class NotificationView(LoginRequiredMixin, TemplateView):

    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/_notifications-timeline.html']
        else:
            return ['dashboard/notifications.html']

    def get_context_data(self, *args, **kwargs):
        context = super(NotificationView, self).get_context_data(
            *args, **kwargs)
        paginate_by = 10 if self.request.is_ajax() else 25
        page = self.request.GET.get("page", 1)

        notifications = self.request.user.notification_set.all()
        paginator = Paginator(notifications, paginate_by)
        try:
            current_page = paginator.page(page)
        except InvalidPage:
            current_page = paginator.page(1)

        context['page'] = current_page
        context['paginator'] = paginator
        return context

    def get(self, *args, **kwargs):
        response = super(NotificationView, self).get(*args, **kwargs)
        un = self.request.user.notification_set.filter(status="new")
        for u in un:
            u.status = "read"
            u.save()
        return response


class CircleLoginView(LoginView):
    form_class = CircleAuthenticationForm

    def get_context_data(self, **kwargs):
        ctx = super(CircleLoginView, self).get_context_data(**kwargs)
        ctx.update({
            'saml2': saml_available,
            'og_image': (settings.DJANGO_URL.rstrip("/") +
                         static("dashboard/img/og.png"))
        })
        return ctx

    def form_valid(self, form):
        user = form.get_user()
        if hasattr(user, "profile") and user.profile.two_factor_secret:
            self.request.session['two-fa-user'] = user.pk
            self.request.session['two-fa-redirect'] = self.get_success_url()
            self.request.session['login-type'] = "password"
            return redirect(reverse("two-factor-login"))
        else:
            response = super(CircleLoginView, self).form_valid(form)
            set_language_cookie(self.request, response)
            return response


class TokenLogin(View):

    token_max_age = 120  # seconds

    @classmethod
    def get_salt(cls):
        return unicode(cls)

    @classmethod
    def get_token(cls, user, sudoer):
        return signing.dumps((sudoer.pk, user.pk),
                             salt=cls.get_salt(), compress=True)

    @classmethod
    def get_token_url(cls, user, sudoer):
        key = cls.get_token(user, sudoer)
        return reverse("dashboard.views.token-login", args=(key, ))

    def get(self, request, token, *args, **kwargs):
        try:
            data = signing.loads(token, salt=self.get_salt(),
                                 max_age=self.token_max_age)
            logger.debug('TokenLogin token data: %s', unicode(data))
            sudoer, user = data
            logger.debug('Extracted TokenLogin data: sudoer: %s, user: %s',
                         unicode(sudoer), unicode(user))
        except (signing.BadSignature, ValueError, TypeError) as e:
            logger.warning('Tried invalid TokenLogin token. '
                           'Token: %s, user: %s. %s',
                           token, unicode(self.request.user), unicode(e))
            raise SuspiciousOperation()
        sudoer = User.objects.get(pk=sudoer)
        if not sudoer.is_superuser:
            raise PermissionDenied()
        user = User.objects.get(pk=user)
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        logger.warning('%s %d logged in as user %s %d',
                       unicode(sudoer), sudoer.pk, unicode(user), user.pk)
        login(request, user)
        messages.info(request, _("Logged in as user %s.") % unicode(user))
        return redirect("/")


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
                messages.success(self.request,
                                 _("Password successfully changed."))

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


class UserCreationView(LoginRequiredMixin, PermissionRequiredMixin,
                       CreateView):
    form_class = UserCreationForm
    model = User
    template_name = 'dashboard/user-create.html'
    permission_required = "auth.add_user"

    def get_template_names(self):
        return ['dashboard/nojs-wrapper.html']

    def get_context_data(self, *args, **kwargs):
        context = super(UserCreationView, self).get_context_data(*args,
                                                                 **kwargs)
        context.update({
            'template': self.template_name,
            'box_title': _('Create a User'),
        })
        return context

    def get_success_url(self):
        return reverse('dashboard.views.profile', args=[self.object.username])

    def get_form_kwargs(self):
        profiles = GroupProfile.get_objects_with_level(
            'owner', self.request.user)
        choices = Group.objects.filter(groupprofile__in=profiles)
        group_pk = self.request.GET.get('group_pk')
        if group_pk:
            try:
                default = choices.get(pk=group_pk)
            except (ValueError, Group.DoesNotExist):
                raise Http404()
        else:
            default = None

        val = super(UserCreationView, self).get_form_kwargs()
        val.update({'choices': choices, 'default': default})
        return val


class ProfileView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    template_name = "dashboard/profile.html"
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"
    form_class = UserEditForm
    success_message = _("Successfully modified user.")

    def get(self, *args, **kwargs):
        user = self.request.user
        target = self.get_object()

        # get the list of groups where the user is operator
        user_g_w_op = GroupProfile.get_objects_with_level("operator", user)
        # get the list of groups the "target" (the profile) is member of
        target_groups = GroupProfile.objects.filter(
            group__in=target.groups.all())
        intersection = set(user_g_w_op).intersection(target_groups)

        # if the intersection of the 2 lists is empty the logged in user
        # has no permission to check the target's profile
        # (except if the user want to see his own profile)
        if not intersection and target != user and not user.is_superuser:
            raise PermissionDenied

        return super(ProfileView, self).get(*args, **kwargs)

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
        if self.request.user.is_superuser:
            context['login_token'] = TokenLogin.get_token_url(
                user, self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        if not request.user.has_perm('auth.change_user'):
            raise PermissionDenied()
        return super(ProfileView, self).post(self, request, *args, **kwargs)

    def get_success_url(self):
        return reverse('dashboard.views.profile',
                       kwargs=self.kwargs)


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


class UserKeyDelete(DeleteViewBase):
    model = UserKey
    success_message = _("SSH key successfully deleted.")

    def get_success_url(self):
        return reverse("dashboard.views.profile-preferences")

    def check_auth(self):
        if self.get_object().user != self.request.user:
            raise PermissionDenied()


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


class ConnectCommandDelete(DeleteViewBase):
    model = ConnectCommand
    success_message = _("Command template successfully deleted.")

    def get_success_url(self):
        return reverse("dashboard.views.profile-preferences")

    def check_auth(self):
        if self.get_object().user != self.request.user:
            raise PermissionDenied()


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


class UserList(LoginRequiredMixin, PermissionRequiredMixin, SingleTableView):
    template_name = "dashboard/user-list.html"
    permission_required = "auth.change_user"
    model = User
    table_class = UserListTable
    table_pagination = True

    def get_context_data(self, *args, **kwargs):
        context = super(UserList, self).get_context_data(*args, **kwargs)
        context['search_form'] = self.search_form
        return context

    def get(self, *args, **kwargs):
        self.search_form = UserListSearchForm(self.request.GET)
        self.search_form.full_clean()

        if self.request.is_ajax():
            users = [
                {'url': reverse("dashboard.views.profile", args=[i.username]),
                 'name': i.get_full_name() or i.username,
                 'org_id': i.profile.org_id,
                 }
                for i in self.get_queryset()]
            return HttpResponse(
                json.dumps(users), content_type="application/json")
        else:
            return super(UserList, self).get(*args, **kwargs)

    def get_queryset(self):
        logger.debug('UserList.get_queryset() called. User: %s',
                     unicode(self.request.user))
        qs = User.objects.all().order_by("-pk")

        q = self.search_form.cleaned_data.get('s')
        if q:
            filters = (Q(username__icontains=q) | Q(email__icontains=q) |
                       Q(profile__org_id__icontains=q))
            for w in q.split()[:3]:
                filters |= (
                    Q(first_name__icontains=w) | Q(last_name__icontains=w))
            qs = qs.filter(filters)

        return qs.select_related("profile")


class EnableTwoFactorView(LoginRequiredMixin, UpdateView):
    model = Profile
    form_class = TwoFactorForm
    template_name = "dashboard/enable-two-factor.html"
    success_url = reverse_lazy("dashboard.views.profile-preferences")

    def get_object(self, queryset=None):
        if self.request.user.is_anonymous():
            raise PermissionDenied

        return self.request.user.profile

    def get_context_data(self, **kwargs):
        ctx = super(EnableTwoFactorView, self).get_context_data(**kwargs)
        random_base32 = pyotp.random_base32()
        ctx['uri'] = pyotp.TOTP(random_base32).provisioning_uri(
            self.request.user.username, issuer_name=settings.TWO_FACTOR_ISSUER)
        ctx['secret'] = random_base32
        return ctx


class DisableTwoFactorView(LoginRequiredMixin, FormView):
    form_class = TwoFactorConfirmationForm
    template_name = "dashboard/disable-two-factor.html"
    success_url = reverse_lazy("dashboard.views.profile-preferences")

    def get_profile(self, queryset=None):
        if self.request.user.is_anonymous():
            raise PermissionDenied

        return self.request.user.profile

    def get_form_kwargs(self):
        kwargs = super(DisableTwoFactorView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        profile = self.get_profile()
        profile.two_factor_secret = ""
        profile.save()
        return super(DisableTwoFactorView, self).form_valid(form)


class TwoFactorLoginView(FormView):
    form_class = TwoFactorConfirmationForm
    template_name = "registration/two-factor-login.html"

    def dispatch(self, *args, **kwargs):
        if not self.request.session.get('two-fa-user'):
            return redirect("/")

        return super(TwoFactorLoginView, self).dispatch(*args, **kwargs)

    def get_user(self):
        return User.objects.get(pk=self.request.session['two-fa-user'])

    def get_form_kwargs(self):
        kwargs = super(TwoFactorLoginView, self).get_form_kwargs()
        kwargs['user'] = self.get_user()
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super(TwoFactorLoginView, self).get_context_data(**kwargs)
        ctx['user'] = self.get_user()
        return ctx

    def form_valid(self, form):
        user = self.get_user()

        if self.request.session['login-type'] == "saml2":
            user.backend = 'common.backends.Saml2Backend'
        else:
            user.backend = 'django.contrib.auth.backends.ModelBackend'

        login(self.request, user)
        response = redirect(self.request.session['two-fa-redirect'])
        set_language_cookie(self.request, response)
        return response


if hasattr(settings, 'SAML_ORG_ID_ATTRIBUTE'):
    from django.http import HttpResponseBadRequest, HttpResponseForbidden
    from django.views.decorators.csrf import csrf_exempt

    from djangosaml2.cache import IdentityCache, OutstandingQueriesCache
    from djangosaml2.conf import get_config
    from djangosaml2.signals import post_authenticated
    from djangosaml2.utils import get_custom_setting
    from saml2.client import Saml2Client
    from saml2.ident import code
    from saml2 import BINDING_HTTP_POST

    @require_POST
    @csrf_exempt
    def circle_assertion_consumer_service(request,
                                          config_loader_path=None,
                                          attribute_mapping=None,
                                          create_unknown_user=None):
        """SAML Authorization Response endpoint
        The IdP will send its response to this view, which
        will process it with pysaml2 help and log the user
        in using the custom Authorization backend or redirect to 2fa
        djangosaml2.backends.Saml2Backend that should be
        enabled in the settings.py
        """
        attribute_mapping = attribute_mapping or get_custom_setting(
            'SAML_ATTRIBUTE_MAPPING', {'uid': ('username', )})
        create_unknown_user = create_unknown_user or get_custom_setting(
            'SAML_CREATE_UNKNOWN_USER', True)
        logger.debug('Assertion Consumer Service started')

        conf = get_config(config_loader_path, request)
        if 'SAMLResponse' not in request.POST:
            return HttpResponseBadRequest(
                'Couldn\'t find "SAMLResponse" in POST data.')
        xmlstr = request.POST['SAMLResponse']
        client = Saml2Client(
            conf, identity_cache=IdentityCache(request.session))

        oq_cache = OutstandingQueriesCache(request.session)
        outstanding_queries = oq_cache.outstanding_queries()

        # process the authentication response
        response = client.parse_authn_request_response(
            xmlstr, BINDING_HTTP_POST, outstanding_queries)
        if response is None:
            logger.error('SAML response is None')
            return HttpResponseBadRequest(
                "SAML response has errors. Please check the logs")

        session_id = response.session_id()
        oq_cache.delete(session_id)

        # authenticate the remote user
        session_info = response.session_info()

        if callable(attribute_mapping):
            attribute_mapping = attribute_mapping()
        if callable(create_unknown_user):
            create_unknown_user = create_unknown_user()

        logger.debug('Trying to authenticate the user')
        user = authenticate(session_info=session_info,
                            attribute_mapping=attribute_mapping,
                            create_unknown_user=create_unknown_user)
        if user is None:
            logger.error('The user is None')
            return HttpResponseForbidden("Permission denied")

        # redirect the user to the view where he came from
        relay_state = request.POST.get('RelayState', '/')
        if not relay_state:
            logger.warning('The RelayState parameter exists but is empty')
            relay_state = settings.LOGIN_REDIRECT_URL
        logger.debug('Redirecting to the RelayState: ' + relay_state)

        if hasattr(user, "profile") and user.profile.two_factor_secret:
            request.session['two-fa-user'] = user.pk
            request.session['two-fa-redirect'] = relay_state
            request.session['login-type'] = "saml2"
            return redirect(reverse("two-factor-login"))
        else:
            login(request, user)

            def _set_subject_id(session, subject_id):
                session['_saml2_subject_id'] = code(subject_id)

            _set_subject_id(request.session, session_info['name_id'])

            logger.debug('Sending the post_authenticated signal')
            post_authenticated.send_robust(sender=user,
                                           session_info=session_info)

            # redirect the user to the view where he came from
            return redirect(relay_state)

    from djangosaml2 import views as saml2_views
    saml2_views.assertion_consumer_service = circle_assertion_consumer_service
