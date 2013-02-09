# -*- coding: utf-8 -*-
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
from school.models import *
import django.contrib.auth as auth
from firewall.tasks import *
import json

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
        'templates': Template.objects.all(),
        'instances': _list_instances(request),
        'groups': request.user.person_set.all()[0].owned_groups.all(),
        'semesters': Semester.objects.all()
        }))

@require_GET
@login_required
def ajax_template_wizard(request):
    return render_to_response('new-template-flow.html', RequestContext(request,{
        'templates': Template.objects.all(),
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
        'id': int(iid),
        'age': inst.get_age(),
        'instances': _list_instances(request),
        'i': inst,
        'booting' : not inst.active_since,
        'ports': inst.firewall_host.list_ports()
        }))

@require_safe
@login_required
def vm_ajax_instance_status(request, iid):
    inst = get_object_or_404(Instance, id=iid, owner=request.user)
    inst.update_state()
    return HttpResponse(json.dumps({'booting': not inst.active_since, 'state': inst.state}))

def boot_token(request, token):
    try:
        id = signing.loads(token, salt='activate')
    except:
        return HttpResponse("Invalid token.")
    inst = get_object_or_404(Instance, id=id)
    if inst.active_since:
        return HttpResponse("Already booted?")
    else:
        inst.active_since = datetime.now()
        inst.save()
        return HttpResponse("KTHXBYE")

class VmPortAddView(View):
    def post(self, request, iid, *args, **kwargs):
        try:
            public = int(request.POST['public'])

            if public >= 22000 and public < 24000:
                raise ValidationError(_("Port number is in a restricted domain (22000 to 24000)."))
            inst = get_object_or_404(Instance, id=iid, owner=request.user)
            inst.firewall_host.add_port(proto=request.POST['proto'], public=public, private=int(request.POST['private']))
            reload_firewall_lock()
            messages.success(request, _(u"Port %d successfully added.") % public)
        except:
            messages.error(request, _(u"Adding port failed."))
#            raise
        return redirect('/vm/show/%d/' % int(iid))

    def get(self, request, iid, *args, **kwargs):
        return redirect('/')

vm_port_add = login_required(VmPortAddView.as_view())

@require_safe
@login_required
@require_GET
def vm_port_del(request, iid, proto, public):
    inst = get_object_or_404(Instance, id=iid, owner=request.user)
    try:
        inst.firewall_host.del_port(proto=proto, public=public)
        reload_firewall_lock()
        messages.success(request, _(u"Port %d successfully removed.") % public)
    except:
        messages.error(request, _(u"Removing port failed."))
    return redirect('/vm/show/%d/' % int(iid))

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

@login_required
@require_POST
def vm_stop(request, iid, *args, **kwargs):
    try:
        get_object_or_404(Instance, id=iid, owner=request.user).stop()
        messages.success(request, _('Virtual machine is successfully stopped.'))
    except:
        messages.error(request, _('Failed to stop virtual machine.'))
    return redirect('/')

@login_required
@require_POST
def vm_resume(request, iid, *args, **kwargs):
    try:
        get_object_or_404(Instance, id=iid, owner=request.user).resume()
        messages.success(request, _('Virtual machine is successfully resumed.'))
    except:
        messages.error(request, _('Failed to resume virtual machine.'))
    return redirect('/')

@login_required
@require_POST
def vm_power_off(request, iid, *args, **kwargs):
    try:
        get_object_or_404(Instance, id=iid, owner=request.user).poweroff()
        messages.success(request, _('Virtual machine is successfully powered off.'))
    except:
        messages.error(request, _('Failed to power off virtual machine.'))
    return redirect('/')

@login_required
@require_POST
def vm_restart(request, iid, *args, **kwargs):
    try:
        get_object_or_404(Instance, id=iid, owner=request.user).restart()
        messages.success(request, _('Virtual machine is successfully restarted.'))
    except:
        messages.error(request, _('Failed to restart virtual machine.'))
    return redirect('/')

# vim: et sw=4 ai fenc=utf8 smarttab :
