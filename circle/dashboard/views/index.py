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

import logging

from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.views.generic import TemplateView

from braces.views import LoginRequiredMixin

from dashboard.models import GroupProfile
from vm.models import Instance, Node, InstanceTemplate
from dashboard.views.vm import vm_ops

from ..store_api import Store

logger = logging.getLogger(__name__)


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
        if user.has_perm('vm.view_statistics'):
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

        # users
        if user.has_module_perms('auth.change_user'):
            users = User.objects.all()
            context.update({
                'users': users[:5],
                'more_users': users.count() - len(users[:5]),
            })

        # template
        if user.has_perm('vm.create_template'):
            context['templates'] = InstanceTemplate.get_objects_with_level(
                'operator', user, disregard_superuser=True).all()[:5]

        # toplist
        if settings.STORE_URL:
            cache_key = "files-%d" % self.request.user.pk
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


class HelpView(TemplateView):

    def get_context_data(self, *args, **kwargs):
        ctx = super(HelpView, self).get_context_data(*args, **kwargs)
        operations = [(o, Instance._ops[o.op])
                      for o in vm_ops.values() if o.show_in_toolbar]
        ctx.update({"saml": hasattr(settings, "SAML_CONFIG"),
                    "operations": operations,
                    "store": settings.STORE_URL})
        return ctx


class ResizeHelpView(TemplateView):
    template_name = "info/resize.html"


class OpenSearchDescriptionView(TemplateView):
    template_name = "dashboard/vm-opensearch.xml"
    content_type = "application/opensearchdescription+xml"

    def get_context_data(self, **kwargs):
        context = super(OpenSearchDescriptionView, self).get_context_data(
            **kwargs)
        context['url'] = self.request.build_absolute_uri(
            reverse("dashboard.views.vm-list"))
        return context
