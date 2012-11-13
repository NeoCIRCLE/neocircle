from datetime import datetime
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core import signing
from django.core.mail import mail_managers, send_mail
from django.db import transaction
from django.forms import ModelForm, Textarea
from django.http import Http404
#from django_shibboleth.forms import BaseRegisterForm
from django.shortcuts import render, render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.utils.translation import get_language as lang
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import *
from django.views.generic import *
from one.models import *
import django.contrib.auth as auth

class LoginView(View):
    def get(self, request, *args, **kwargs):
        nex = '/'
        try:
            nex = request.GET['next']
        except:
            pass
        return render_to_response("login.html", RequestContext(request,{'next': nex}))
    def post(self, request, *args, **kwargs):
        if request.POST['pw'] != 'ezmiez':
            return redirect('/')
        p, created = User.objects.get_or_create(username=request.POST['neptun'])
	if created:
            p.set_unusable_password()
        if not p.email:
            p.email = "%s@nc.hszk.bme.hu" % p.username
        p.save()
        if not p.person_set.exists():
            person = Person(neptun = p.username)
            p.person_set.add(person)
            p.save()
        p.backend = 'django.contrib.auth.backends.ModelBackend'
        auth.login(request, p)
        path = '/'
        try:
            path = request.POST['next']
            if not path.startswith("/"):
                path = '/'
        except:
            pass
        return redirect(path)

def logout(request):
        auth.logout(request)
        return redirect('/')

def _list_instances(request):
    instances = Instance.objects.exclude(state='DONE').filter(owner=request.user)
    for i in instances:
        i.update_state()
    return instances

@require_GET
@login_required
def home(request):
    return render_to_response("home.html", RequestContext(request,{
	"templates": Template.objects.all(),
        'instances': _list_instances(request),
        }))

@require_POST
@login_required
def vm_new(request, template):
    m = get_object_or_404(Template, pk=template)
    try:
        i = Instance.submit(m, request.user)
        return redirect(i)
    except:
        raise
        messages.error(request, _('Failed to create virtual machine.'))
        return redirect('/')

class VmListView(ListView):
    context_object_name = 'instances'
    template_name = 'list.html'

    def get_queryset(self):
        self.profile = request.user
        return Instance.objects.filter(owner=self.profile)

vm_list = login_required(VmListView.as_view())

@require_safe
@login_required
def vm_show(request, iid):
    inst = get_object_or_404(Instance, id=iid, owner=request.user)
    inst.update_state()
    return render_to_response("show.html", RequestContext(request,{
	'uri': inst.get_connect_uri(),
	'state': inst.state,
	'name': inst.name,
	'id': iid,
        'age': inst.get_age(),
        'instances': _list_instances(request),
        'i': inst,
	'booting' : inst.active_since,
        }))

class VmDeleteView(View):
    def post(self, request, iid, *args, **kwargs):
        try:
            get_object_or_404(Instance, id=iid, owner=request.user).delete()
            messages.success(request, _('Virtual machine is successfully deleted.'))
        except:
            messages.error(request, _('Failed to delete virtual machine.'))
        return redirect('/')

    def get(self, request, iid, *args, **kwargs):
        i = get_object_or_404(Instance, id=iid, owner=request.user)
        return render_to_response("confirm_delete.html", RequestContext(request,{
            'i': i}))

vm_delete = login_required(VmDeleteView.as_view())


def vm_active(request, token):
    id = signing.loads(token, salt='activate', max_age=300)
    vm = get_object_or_404(Instance, id=id)
    vm.active_since = datetime.now()
    vm.save()
    return HttpResponse("Ok.", content_type="text/plain")

# vim: et sw=4 ai fenc=utf8 smarttab :
