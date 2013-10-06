import re

from django.contrib.auth.models import User, Group
from django.core import signing
from django.shortcuts import redirect
from django.views.generic import TemplateView, DetailView, View
from django.views.generic.detail import SingleObjectMixin

from django_tables2 import SingleTableView

from vm.models import Instance

from .tables import VmListTable
from .utils import get_acl_data, set_acl_level


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
