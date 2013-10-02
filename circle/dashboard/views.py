from django.core import signing
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView, DetailView

from django_tables2 import SingleTableView
from guardian.shortcuts import (get_users_with_perms, get_groups_with_perms,
                                get_perms)
from tables import VmListTable

from vm.models import Instance

from .tables import VmListTable


class IndexView(TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        if self.request.user.is_authenticated():
            user = self.request.user
        else:
            user = None

        context = super(IndexView, self).get_context_data(**kwargs)
        context.update({
            'instances': Instance.objects.filter(owner=user),
        })
        return context


def first_common_element(a, b):
    for i in a:
        if i in b:
            return i
    return None


def get_acl_data(obj):
    levels = obj._meta.permissions
    levelids = [id for (id, name) in levels]
    users = get_users_with_perms(obj, with_group_users=False)
    users = [{'user': u,
              'perm': first_common_element(levelids, get_perms(u, obj))}
             for u in users]
    groups = get_groups_with_perms(obj)
    groups = [{'group': g,
               'perm': first_common_element(levelids, get_perms(g, obj))}
              for g in groups]
    return {'users': users, 'groups': groups, 'levels': levels,
            'url': obj.get_absolute_url()}


class VmDetailView(DetailView):
    template_name = "dashboard/vm-detail.html"
    queryset = Instance.objects.all()

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        instance = context['instance']
        if instance.node:
            port = instance.vnc_port
            host = instance.node.host.ipv4
            value = signing.dumps({'host': host,
                                   'port': port}, key='asdasd')
            context.update({
                'vnc_url': '%s' % value
            })
        context['acl'] = get_acl_data(instance)
        return context


class VmList(SingleTableView):
    template_name = "dashboard/vm-list.html"
    model = Instance
    table_class = VmListTable
