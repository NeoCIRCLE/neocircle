# -*- coding: utf-8 -*-
from datetime import datetime
from django.conf import settings
from datetime import timedelta as td
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core import signing, urlresolvers
from django.core.mail import mail_managers, send_mail
from django.db import transaction
from django.forms import ModelForm, Textarea
from django.http import Http404
from django.shortcuts import render, render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.utils.translation import get_language as lang
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import *
from django.views.generic import *
from firewall.tasks import *
from one.models import *
from school.models import *
import django.contrib.auth as auth
import json
import logging
import subprocess

store_settings = settings.STORE_SETTINGS
logger = logging.getLogger(__name__)

def _list_instances(request):
    instances = Instance.objects.exclude(state='DONE').filter(owner=request.user)
    instances = instances.exclude(state='DONE')
    return instances

def info(request):
    return render_to_response("info.html", RequestContext(request, {}))

def index(request):
    if request.user.is_authenticated():
        return redirect(home)
    else:
        return redirect(info)


@require_GET
@login_required
def home(request):
    instances = _list_instances(request)
    shares = [s for s in request.user.person_set.all()[0].get_shares()]
    for i, s in enumerate(shares):
        s.running_shared = s.instance_set.all().exclude(state="DONE").filter(owner=request.user).count()
        shares[i] = s
    try:
        details = UserCloudDetails.objects.get(user=request.user)
    except UserCloudDetails.DoesNotExist:
        details = UserCloudDetails(user=request.user)
        details.save()
    try:
        generated_public_key = details.ssh_key.id
    except:
        generated_public_key = -1
    return render_to_response("home.html", RequestContext(request, {
        'instances': instances,
        'shares': shares,
        'templates': Template.objects.filter(state='READY'),
        'mytemplates': Template.objects.filter(owner=request.user),
        'groups': request.user.person_set.all()[0].owned_groups.all(),
        'semesters': Semester.objects.all(),
        'userdetails': details,
        'keys': request.user.sshkey_set.exclude(id=generated_public_key).all(),
        'storeserv': store_settings['store_public'],
        }))

@login_required
def ajax_template_delete(request):
    try:
        template_id = request.POST['id']
    except:
        return HttpResponse(unicode(_("Invalid template ID.")), status=404)
    template = get_object_or_404(Template, id=template_id)
    if template.running_instances() > 0:
        return HttpResponse(unicode(_("There are running instances of this template.")), status=404)
    elif template.share_set.exists():
        return HttpResponse(unicode(_("Template is still shared.")), status=404)
    elif template.owner != request.user:
        return HttpResponse(unicode(_("You don't have permission to delete this template.")), status=404)
    else:
        if template.safe_delete():
            return HttpResponse(unicode(_("Template successfully deleted.")))
        else:
            return HttpResponse(unicode(_("Unexpected error happened.")), status=404)

def ajax_template_name_unique(request):
    name = request.GET['name']
    s = "True"
    if Template.objects.filter(name=name).exists():
        s = "False"
    return HttpResponse(s)

@login_required
def vm_credentials(request, iid):
    try:
        vm = get_object_or_404(Instance, pk=iid, owner=request.user)
        is_ipv6 = len(request.META["REMOTE_ADDR"].split('.')) == 1
        vm.hostname_v4 = vm.get_connect_host(use_ipv6=False)
        vm.hostname_v6 = vm.get_connect_host(use_ipv6=True)
        vm.is_ipv6 = is_ipv6
        vm.port_v4 = vm.get_port(use_ipv6=False)
        vm.port_v6 = vm.get_port(use_ipv6=True)
        return render_to_response('vm-credentials.html', RequestContext(request, { 'i' : vm }))
    except:
        return HttpResponse(_("Could not get Virtual Machine credentials."), status=404)
        messages.error(request, _('Failed to power off virtual machine.'))

class AjaxTemplateWizard(View):
    def get(self, request, *args, **kwargs):
        return render_to_response('new-template-flow-1.html', RequestContext(request, {
            'templates': [t for t in Template.objects.filter(public=True).all()] +
                         [t for t in Template.objects.filter(owner=request.user).all()],
            }))
    def post(self, request, *args, **kwargs):
        base = get_object_or_404(Template, id=request.POST['base'])
        if base.owner != request.user and not base.public and not request.user.is_superuser:
            raise PermissionDenied()
        try:
            maxshare = Template.objects.order_by('-pk')[0].pk + 1
        except:
            maxshare = 1
        return render_to_response('new-template-flow.html', RequestContext(request, {
            'sizes': InstanceType.objects.all(),
            'base': base,
            'maxshare': maxshare,
            }))
ajax_template_wizard = login_required(AjaxTemplateWizard.as_view())

class AjaxTemplateEditWizard(View):
    def get(self, request, id, *args, **kwargs):
        template = get_object_or_404(Template, id=id)
        if template.owner != request.user and not template.public and not request.user.is_superuser:
            raise PermissionDenied()
        return render_to_response('edit-template-flow.html', RequestContext(request, {
            'sizes': InstanceType.objects.all(),
            'template': template,
            }))
    def post(self, request, id, *args, **kwargs):
        template = get_object_or_404(Template, id=id)
        user_details = UserCloudDetails.objects.get(user=request.user)
        if template.owner != request.user and not template.public and not request.user.is_superuser:
            raise PermissionDenied()
        instance_type = get_object_or_404(InstanceType, id=request.POST['size'])
        current_used_share_quota = user_details.get_weighted_share_count()
        current_used_share_quota_without_template = current_used_share_quota - template.get_share_quota_usage_for(request.user)
        new_quota_for_current_template = template.get_share_quota_usage_for_user_with_type(instance_type, request.user)
        new_used_share_quota = current_used_share_quota_without_template + new_quota_for_current_template
        allow_type_modify = True if new_used_share_quota <= user_details.share_quota else False
        if not allow_type_modify:
            messages.error(request, _('You do not have enough free share quota.'))
            return redirect(home)
        template.instance_type = instance_type
        template.description = request.POST['description']
        template.name = request.POST['name']
        template.save()
        return redirect(home)

ajax_template_edit_wizard = login_required(AjaxTemplateEditWizard.as_view())


class AjaxShareWizard(View):
    def get(self, request, id, gid=None, *args, **kwargs):
        det = UserCloudDetails.objects.get(user=request.user)
        if det.get_weighted_share_count() >= det.share_quota:
            return HttpResponse(unicode(_('You do not have any free share quota.')))
        types = TYPES_L
        types[0]['default'] = True
        for i, t in enumerate(types):
            t['deletex'] = datetime.now() + td(seconds=1) + t['delete'] if t['delete'] else None
            t['suspendx'] = datetime.now() + td(seconds=1) + t['suspend'] if t['suspend'] else None
            types[i] = t
        if gid:
            gid = get_object_or_404(Group, id=gid)

        return render_to_response('new-share.html', RequestContext(request, {
            'base': get_object_or_404(Template, id=id),
            'groups': request.user.person_set.all()[0].owned_groups.all(),
            'types': types,
            'group': gid,
            }))
    def post(self, request, id, gid=None, *args, **kwargs):
        det = UserCloudDetails.objects.get(user=request.user)
        base = get_object_or_404(Template, id=id)
        if base.owner != request.user and not base.public and not request.user.is_superuser:
            raise PermissionDenied()
        group = None
        if gid:
            group = get_object_or_404(Group, id=gid)
        else:
            group = get_object_or_404(Group, id=request.POST['group'])

        if not group.owners.filter(user=request.user).exists():
            raise PermissionDenied()
        stype = request.POST['type']
        if not stype in TYPES.keys():
            raise PermissionDenied()
        il = request.POST['instance_limit']
        if det.get_weighted_share_count() + int(il)*base.instance_type.credit > det.share_quota:
            messages.error(request, _('You do not have enough free share quota.'))
            return redirect('/')
        s = Share.objects.create(name=request.POST['name'], description=request.POST['description'],
                type=stype, instance_limit=il, per_user_limit=request.POST['per_user_limit'],
                group=group, template=base, owner=request.user)
        messages.success(request, _('Successfully shared %s.') % base)
        return redirect(group)
ajax_share_wizard = login_required(AjaxShareWizard.as_view())

class AjaxShareEditWizard(View):
    def get(self, request, id, *args, **kwargs):
        det = UserCloudDetails.objects.get(user=request.user)
        if det.get_weighted_share_count() > det.share_quota:
            logger.warning('[one] User %s ha more used share quota, than its limit, how is that possible? (%d > %d)',
                str(request.user),
                det.get_weighted_share_count(),
                det.share_quota)
            return HttpResponse(unicode(_('You do not have any free share quota.')))
        types = TYPES_L
        for i, t in enumerate(types):
            t['deletex'] = datetime.now() + td(seconds=1) + t['delete'] if t['delete'] else None
            t['suspendx'] = datetime.now() + td(seconds=1) + t['suspend'] if t['suspend'] else None
            types[i] = t
        share = get_object_or_404(Share, id=id)
        return render_to_response('edit-share.html', RequestContext(request, {
            'share': share,
            'types': types,
            }))
    def post(self, request, id, *args, **kwargs):
        det = UserCloudDetails.objects.get(user=request.user)
        share = get_object_or_404(Share, id=id)
        if share.owner != request.user and not request.user.is_superuser:
            raise PermissionDenied()
        stype = request.POST['type']
        if not stype in TYPES.keys():
            raise PermissionDenied()
        instance_limit = int(request.POST['instance_limit'])
        current_used_share_quota = det.get_weighted_share_count()
        current_used_share_quota_without_current_share = current_used_share_quota - share.get_used_quota()
        new_quota_for_current_share = instance_limit * share.template.get_credits_per_instance()
        new_used_share_quota = current_used_share_quota_without_current_share + new_quota_for_current_share
        allow_stype_modify = True if new_used_share_quota <= det.share_quota else False
        if not allow_stype_modify:
            messages.error(request, _('You do not have enough free share quota.'))
            return redirect(share.group)
        share.name = request.POST['name']
        share.description = request.POST['description']
        share.type = stype
        share.instance_limit = instance_limit
        share.per_user_limit = request.POST['per_user_limit']
        share.owner = request.user
        share.save()
        messages.success(request, _('Successfully edited share %s.') % share)
        return redirect(share.group)
ajax_share_edit_wizard = login_required(AjaxShareEditWizard.as_view())


@require_POST
@login_required
def vm_saveas(request, vmid):
    inst = get_object_or_404(Instance, pk=vmid)
    if inst.owner != request.user and not request.user.is_superuser:
        raise PermissionDenied()
    inst.save_as()
    messages.success(request, _("Template is being saved..."))
    return redirect(inst)

def vm_new_ajax(request, template):
    return vm_new(request, template, redir=False)

def _redirect_or_201(path, redir):
    if redir:
        return redirect(path)
    else:
        response = HttpResponse("Created", status=201)
        response['Location'] = path
        return response

def _template_for_save(base, request):
    if base.owner != request.user and not base.public and not request.user.is_superuser:
        raise PermissionDenied()
    name = request.POST['name']
    t = Template.objects.create(name=name, disk=base.disk, instance_type_id=request.POST['size'], network=base.network, owner=request.user)
    t.access_type = base.access_type
    t.description = request.POST['description']
    t.system = base.system
    t.save()
    return t

def _check_quota(request, template, share):
    """
    Returns if the given request is permitted to run the new vm.
    """
    det = UserCloudDetails.objects.get(user=request.user)
    if det.get_weighted_instance_count() + template.instance_type.credit > det.instance_quota:
        messages.error(request, _('You do not have any free quota. You can not launch this until you stop an other instance.'))
        return False
    if share:
        if share.get_running() + 1 > share.instance_limit:
            messages.error(request, _('The share does not have any free quota. You can not launch this until someone stops an instance.'))
            return False
        elif share.get_running_or_stopped(request.user) + 1 > share.per_user_limit:
            messages.error(request, _('You do not have any free quota for this share. You can not launch this until you stop an other instance.'))
            return False
        if not share.group.members.filter(user=request.user) and not share.group.owners.filter(user=request.user):
            messages.error(request, _('You are not a member of the share group.'))
            return False
    return True

@require_POST
@login_required
def vm_new(request, template=None, share=None, redir=True):
    base = None
    extra = ''
    if template:
        base = get_object_or_404(Template, pk=template)
    else:
        share = get_object_or_404(Share, pk=share)
        base = share.template

    go = True
    if "name" in request.POST:
        try:
            base = _template_for_save(base, request)
            extra = "<RECONTEXT>YES</RECONTEXT>"
        except:
            messages.error(request, _('Can not create template.'))
            go = False
    go = go and _check_quota(request, base, share)

    if not share and not base.public and base.owner != request.user:
        messages.error(request, _('You have no permission to try this instance without a share. Launch a new instance through a share.'))
        go = False
    type = share.type if share else 'LAB'
    TYPES[type]['suspend']
    time_of_suspend = TYPES[type]['suspend']+datetime.now()
    if TYPES[type]['delete']:
        time_of_delete = TYPES[type]['delete']+datetime.now()
    else:
        time_of_delete = None
    inst = None
    if go:
        try:
            inst = Instance.submit(base, request.user, extra=extra, share=share)
        except Exception as e:
            logger.error('Failed to create virtual machine.' + unicode(e))
            messages.error(request, _('Failed to create virtual machine.'))
            inst = None
        if inst:
            inst.waiting = True
            inst.time_of_suspend = time_of_suspend
            inst.time_of_delete = time_of_delete
            inst.save()
    elif extra and base:
        base.delete()
    return _redirect_or_201(inst.get_absolute_url() if inst else '/', redir)

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
    try:
        ports = inst.firewall_host.list_ports()
    except:
        ports = None
    try:
        details = UserCloudDetails.objects.get(user=request.user)
    except UserCloudDetails.DoesNotExist:
        details = UserCloudDetails(user=request.user)
        details.save()
    is_ipv6 = len(request.META["REMOTE_ADDR"].split('.')) == 1
    inst.is_ipv6 = is_ipv6
    inst.hostname_v4 = inst.get_connect_host(use_ipv6=False)
    inst.hostname_v6 = inst.get_connect_host(use_ipv6=True)
    inst.port_v4 = inst.get_port(use_ipv6=False)
    inst.port_v6 = inst.get_port(use_ipv6=True)
    return render_to_response("show.html", RequestContext(request,{
        'uri': inst.get_connect_uri(),
        'state': inst.state,
        'name': inst.name,
        'id': int(iid),
        'age': inst.get_age(),
        'instances': _list_instances(request),
        'i': inst,
        'booting' : not inst.active_since,
        'ports': ports,
        'userdetails': details
        }))

@require_safe
@login_required
def vm_ajax_instance_status(request, iid):
    inst = get_object_or_404(Instance, id=iid, owner=request.user)
    return HttpResponse(json.dumps({
        'booting': not inst.active_since,
        'state': inst.state,
        'waiting': inst.waiting,
        'template': {
            'state': inst.template.state
        }}))

@login_required
def vm_ajax_rename(request, iid):
    inst = get_object_or_404(Instance, id=iid, owner=request.user)
    inst.name = request.POST['name']
    inst.save()
    return HttpResponse(json.dumps({'name': inst.name}))

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
            port = int(request.POST['port'])
            inst = get_object_or_404(Instance, id=iid, owner=request.user)
            if inst.nat:
                inst.firewall_host.add_port(proto=request.POST['proto'],
                        public=None, private=port)
            else:
                inst.firewall_host.add_port(proto=request.POST['proto'],
                        public=port, private=None)

        except:
            messages.error(request, _(u"Adding port failed."))
        else:
            messages.success(request, _(u"Port %d successfully added.") % port)
        return redirect('/vm/show/%d/' % int(iid))

    def get(self, request, iid, *args, **kwargs):
        return redirect('/')

vm_port_add = login_required(VmPortAddView.as_view())

@require_safe
@login_required
@require_GET
def vm_port_del(request, iid, proto, private):
    inst = get_object_or_404(Instance, id=iid, owner=request.user)
    try:
        inst.firewall_host.del_port(proto=proto, private=private)
        messages.success(request, _(u"Port %s successfully removed.") %
                private)
    except:
        messages.error(request, _(u"Removing port failed."))
    return redirect('/vm/show/%d/' % int(iid))

class VmDeleteView(View):
    def post(self, request, iid, *args, **kwargs):
        try:
            inst = get_object_or_404(Instance, id=iid, owner=request.user)
            if inst.template.state != 'READY' and inst.template.owner == request.user:
                inst.template.delete()
            inst.one_delete()
            messages.success(request, _('Virtual machine is successfully deleted.'))
        except:
            messages.error(request, _('Failed to delete virtual machine.'))
        if request.is_ajax():
            return HttpResponse("")
        else:
            return redirect('/')

    def get(self, request, iid, *args, **kwargs):
        i = get_object_or_404(Instance, id=iid, owner=request.user)
        return render_to_response("confirm_delete.html", RequestContext(request, {
            'i': i}))

vm_delete = login_required(VmDeleteView.as_view())

@login_required
#@require_POST
def vm_unshare(request, id, *args, **kwargs):
    s = get_object_or_404(Share, id=id)
    g = s.group
    if not g.owners.filter(user=request.user).exists():
        raise PermissionDenied()
    try:
        if s.get_running_or_stopped() > 0:
            messages.error(request, _('There are machines running of this share.'))
        else:
            s.delete()
            messages.success(request, _('Share is successfully removed.'))
    except:
        messages.error(request, _('Failed to remove share.'))
    return redirect(g)

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
        obj = get_object_or_404(Instance, id=iid, owner=request.user)
        obj.resume()
        messages.success(request, _('Virtual machine is successfully resumed.'))
    except:
        messages.error(request, _('Failed to resume virtual machine.'))
    try:
        obj.renew()
    except:
        pass
    return redirect('/')

@login_required
@require_POST
def vm_renew(request, which, iid, *args, **kwargs):
    try:
        vm = get_object_or_404(Instance, id=iid, owner=request.user)
        vm.renew()
        messages.success(request, _('Virtual machine is successfully renewed.'))
    except:
        messages.error(request, _('Failed to renew virtual machine.'))
        return redirect('/')
    return render_to_response('box/vm/entry.html', RequestContext(request, {
            'vm': vm
        }))

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

@login_required
@require_POST
def key_add(request):
    try:
        key=SshKey()
        key.key=request.POST['key']
        key.user=request.user
        key.full_clean()
        key.save()
        _update_keys(request.user)
    except ValidationError as e:
        for m in e.messages:
            messages.error(request, m)

    except:
        messages.error(request, _('Failed to add public key.'))
    else:
        messages.success(request, _('Public key successfully added.'))
    return redirect('/')

@login_required
@require_POST
def key_ajax_delete(request):
    try:
        key=get_object_or_404(SshKey, id=request.POST['id'], user=request.user)
        key.delete()
        _update_keys(request.user)
    except:
        messages.error(request, _('Failed to delete public key'))
    return HttpResponse('OK')

@login_required
@require_POST
def key_ajax_reset(request):
    try:
        det=UserCloudDetails.objects.get(user=request.user)
        det.reset_smb()
        det.reset_keys()
        _update_keys(request.user)
    except:
        messages.error(request, _('Failed to reset keys'))
    return HttpResponse('OK')

def _update_keys(user):
    details = user.cloud_details
    password = details.smb_password
    key_list = []
    for key in user.sshkey_set.all():
        key_list.append(key.key)
    user = user.username
    StoreApi.updateauthorizationinfo(user, password, key_list)

def stat(request):
    values = subprocess.check_output(['/opt/webadmin/cloud/miscellaneous/stat/stat_wrap.sh'])
  #  values = '''
  #  {"CPU": {"USED_CPU": 2, "ALLOC_CPU": 0,
  #  "FREE_CPU": 98}, "MEM": {"FREE_MEM": 1685432, "ALLOC_MEM":0,
  #  "USED_MEM": 366284}}'''
    stat_dict = json.loads(values)
    return  HttpResponse(render_to_response("stat.html", RequestContext(
                request, {
                    'STAT' : stat_dict,
                }
            )))

def sites(request, site):
    if site in [ "legal", "policy", "help", "support", "changelog", ]:
        return render_to_response("sites/%s.html" % site, RequestContext(request, {}))
    else:
        return redirect(home)

# vim: et sw=4 ai fenc=utf8 smarttab :
