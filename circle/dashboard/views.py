import re

from django.contrib.auth.models import User, Group
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.views.generic import TemplateView, DetailView, View
from django.views.generic.detail import SingleObjectMixin

from django_tables2 import SingleTableView

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


def get_acl_data(obj):
    levels = obj.ACL_LEVELS
    users = obj.get_users_with_level()
    users = [{'user': u, 'level': l} for u, l in users]
    groups = obj.get_groups_with_level()
    groups = [{'group': g, 'level': l} for g, l in groups]
    return {'users': users, 'groups': groups, 'levels': levels,
            'url': reverse('dashboard.views.vm-acl', args=[obj.pk])}


class VmDetailView(DetailView):
    template_name = "dashboard/vm-detail.html"
    model = Instance

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


class AclUpdateView(View, SingleObjectMixin):

    def post(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance.has_level(request.user, "owner"):
            raise PermissionDenied()
        for key, value in request.POST.items():
            m = re.match('perm-([ug])-(\d+)', key)
            if m:
                type, id = m.groups()
                entity = {'u': User, 'g': Group}[type].objects.get(id=id)
                instance.set_level(entity, value)

        name = request.POST['perm-new-name']
        value = request.POST['perm-new']
        if name:
            try:
                entity = User.objects.get(username=name)
            except User.DoesNotExist:
                entity = Group.objects.get(name=name)
            instance.set_level(entity, value)
        return redirect(instance)


class VmList(SingleTableView):
    template_name = "dashboard/vm-list.html"
    model = Instance
    table_class = VmListTable
    table_pagination = False
