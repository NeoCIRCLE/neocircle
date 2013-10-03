import re

from django.contrib.auth.models import User, Group
from django.core import signing
from django.shortcuts import redirect
from django.views.generic import TemplateView, DetailView, UpdateView

from django_tables2 import SingleTableView
from guardian.shortcuts import (get_users_with_perms, get_groups_with_perms,
                                get_perms, remove_perm, assign_perm)

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


def split(t, at):
    """
    Split collection at first occurance of given element.

    >>> split("FooBar", "B")
    ('Foo', 'Bar')
    >>> split(range(5), 2)
    ([0, 1], [2, 3, 4])
    """

    pos = t.index(at)
    return t[:pos], t[pos:]


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


def set_acl_level(obj, whom, level):
    levels = obj._meta.permissions
    levelids = [id for (id, name) in levels]
    to_remove, to_add = split(levelids, level)
    for p in to_remove:
        remove_perm(p, whom, obj)
    for p in to_add:
        assign_perm(p, whom, obj)


class VmDetailView(UpdateView):
    template_name = "dashboard/vm-detail.html"
    queryset = Instance.objects.all()

    def get_context_data(self, **kwargs):
        context = super(VmDetailView, self).get_context_data(**kwargs)
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

    def post(self, request, *args, **kwargs):
        super(VmDetailView, self).post(request, *args, **kwargs)
        context = self.get_context_data(**kwargs)
        instance = context['instance']
        for key, value in request.POST.items():
            m = re.match('perm-([ug])-(\d+)', key)
            if m:
                type, id = m.groups()
                entity = {'u': User, 'g': Group}[type].objects.get(id=id)
                set_acl_level(instance, entity, value)

        name = request.POST['perm-new-name']
        value = request.POST['perm-new']
        if name:
            try:
                entity = User.objects.get(username=name)
            except User.DoesNotExist:
                entity = Group.objects.get(name=name)
            set_acl_level(instance, entity, value)
        return redirect(instance)


class VmList(SingleTableView):
    template_name = "dashboard/vm-list.html"
    model = Instance
    table_class = VmListTable
