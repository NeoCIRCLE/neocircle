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
import re
from collections import OrderedDict
from urlparse import urljoin

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DetailView, View
from django.views.generic.detail import SingleObjectMixin

from braces.views import LoginRequiredMixin
from braces.views._access import AccessMixin
from celery.exceptions import TimeoutError

from common.models import HumanReadableException, HumanReadableObject
from ..models import GroupProfile

logger = logging.getLogger(__name__)
saml_available = hasattr(settings, "SAML_CONFIG")


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


def search_user(keyword):
    try:
        return User.objects.get(username=keyword)
    except User.DoesNotExist:
        try:
            return User.objects.get(profile__org_id=keyword)
        except User.DoesNotExist:
            return User.objects.get(email=keyword)


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

    def create_fake_get(self):
        self.request.GET = self._parse_get(self.request.GET)

    def _parse_get(self, GET_dict):
        """
        Returns a new dict from request's GET dict to filter the vm list
        For example: "name:xy node:1" updates the GET dict
                     to resemble this URL ?name=xy&node=1

        "name:xy node:1".split(":") becomes ["name", "xy node", "1"]
        we pop the the first element and use it as the first dict key
        then we iterate over the rest of the list and split by the last
        whitespace, the first part of this list will be the previous key's
        value, then last part of the list will be the next key.
        The final dict looks like this: {'name': xy, 'node':1}

        >>> f = FilterMixin()
        >>> o = f._parse_get({'s': "hello"}).items()
        >>> sorted(o) # doctest: +ELLIPSIS
        [(u'name', u'hello'), (...)]
        >>> o = f._parse_get({'s': "name:hello owner:test"}).items()
        >>> sorted(o) # doctest: +ELLIPSIS
        [(u'name', u'hello'), (u'owner', u'test'), (...)]
        >>> o = f._parse_get({'s': "name:hello ws node:node 3 oh"}).items()
        >>> sorted(o) # doctest: +ELLIPSIS
        [(u'name', u'hello ws'), (u'node', u'node 3 oh'), (...)]
        """
        s = GET_dict.get("s")
        fake = GET_dict.copy()
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
            for k, v in got.iteritems():
                fake[k] = v
        return fake

    def create_acl_queryset(self, model):
        cleaned_data = self.search_form.cleaned_data
        stype = cleaned_data.get('stype', "all")
        superuser = stype == "all"
        shared = stype == "shared" or stype == "all"
        level = "owner" if stype == "owned" else "user"
        queryset = model.get_objects_with_level(
            level, self.request.user,
            group_also=shared, disregard_superuser=not superuser,
        )
        return queryset


class CheckedDetailView(LoginRequiredMixin, DetailView):
    read_level = 'user'

    def get_has_level(self):
        return self.object.has_level

    def get_context_data(self, **kwargs):
        context = super(CheckedDetailView, self).get_context_data(**kwargs)
        if not self.get_has_level()(self.request.user, self.read_level):
            raise PermissionDenied()
        return context


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
            return HttpResponseRedirect("%s#activity" %
                                        self.object.get_absolute_url())

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


class GraphMixin(object):
    graph_time_options = [
        {'time': "1h", 'name': _("1 hour")},
        {'time': "1d", 'name': _("1 day")},
        {'time': "1w", 'name': _("1 week")},
        {'time': "30d", 'name': _("1 month")},
        {'time': "26w", 'name': _("6 months")},
    ]
    default_graph_time = "6h"

    def get_context_data(self, *args, **kwargs):
        context = super(GraphMixin, self).get_context_data(*args, **kwargs)
        graph_time = self.request.GET.get("graph_time",
                                          self.default_graph_time)
        if not re.match("^[0-9]{1,2}[hdwy]$", graph_time):
            messages.warning(self.request, _("Bad graph time format, "
                                             "available periods are: "
                                             "h, d, w, and y."))
            graph_time = self.default_graph_time
        context['graph_time'] = graph_time
        self.graph_time_options = (
            self.graph_time_options +
            [{'time': self.default_graph_time, 'name': _("default")}]
        )
        context['graph_time_options'] = self.graph_time_options
        return context


def absolute_url(url):
    return urljoin(settings.DJANGO_URL, url)
