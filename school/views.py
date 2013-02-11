from datetime import datetime
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group as AGroup
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core import signing
from django.core.mail import mail_managers, send_mail
from django.db import transaction
from django.forms import ModelForm, Textarea
from django.http import Http404
from django.shortcuts import render, render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.utils.http import is_safe_url
from django.utils.translation import get_language as lang
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import *
from django.views.generic import *
from one.models import *
from school.models import *
import django.contrib.auth as auth
import logging
import json
import re
from django.views.decorators.csrf import ensure_csrf_cookie

logger = logging.getLogger(__name__)

def logout(request):
    auth.logout(request)
    return redirect('/Shibboleth.sso/Logout?return=https%3a%2f%2fcloud.ik.bme.hu%2f')

@ensure_csrf_cookie
def login(request):
    try:
        user = User.objects.get(username=request.META['niifPersonOrgID'])
    except KeyError:
        messages.error(request, _('EduID is not available.'))
        return redirect('/admin')
    except User.DoesNotExist:
        user = User(username=request.META['niifPersonOrgID'])
        user.set_unusable_password()
    user.first_name = request.META['givenName']
    user.last_name = request.META['sn']
    user.email = request.META['email']
    user.save()
    p, created = Person.objects.get_or_create(code=user.username)
    p.user_id = user.id
    p.save()

    try:
        sem = Semester.get_current()

        attended = request.META['HTTP_NIIFEDUPERSONATTENDEDCOURSE']
        if attended == '':
            attended = []
        else:
            attended = attended.split(';')
        for c in attended:
            try:
                co = Course.objects.get(code=c)
            except Exception as e:
                logger.warning("Django could not get Course %s: %s" % (c, e))
                continue
            g = co.get_or_create_default_group()
            if p.course_groups.filter(semester=sem, course=co).count() == 0:
                try:
                    g.members.add(p)
                    g.save()
                    messages.info(request, _('Course "%s" added.') % g.course)
                    logger.warning('Django Course "%s" added.' % g.course)
                except Exception as e:
                    messages.error(request, _('Failed to add course "%s".') % g.course)
                    logger.warning("Django ex %s" % e)
    except ValidationError as e:
        logger.warning("Django ex4 %s" % e)

    held = request.META['HTTP_NIIFEDUPERSONHELDCOURSE']
    if held == '':
        held = []
    else:
        held = held.split(';')
    for c in held:
        co, created = Course.objects.get_or_create(code=c)
        if created:
            logger.warning("Django Course %s created" % c)
        g = co.get_or_create_default_group()
        try:
            co.owners.add(p)
            g.owners.add(p)
            messages.info(request, _('Course "%s" ownership added.') % g.course)
        except Exception as e:
            messages.error(request, _('Failed to add course "%s" ownership.') % g.course)
            logger.warning("Django ex %s" % e)
        co.save()
        g.save()


    affiliation = request.META['affiliation']
    if affiliation == '':
        affiliation = []
    else:
        affiliation = affiliation.split(';')
    for a in affiliation:
        g, created = AGroup.objects.get_or_create(name=a)
        user.groups.add(g)
        try:
            g = Group.objects.filter(name=a)[0]
            g.members.add(p)
            g.save()
            logger.warning("Django affiliation group %s added to %s" % (a, p))
        except e as Exception:
            logger.warning("Django FAIL affiliation group %s added to %s %s" % (a, p, e))
    user.save()

    p.save()
    user.backend = 'django.contrib.auth.backends.ModelBackend'
    auth.login(request, user)
    logger.warning("Shib login with %s" % request.META)


    redirect_to = request.REQUEST.get(auth.REDIRECT_FIELD_NAME, '')
    if not is_safe_url(url=redirect_to, host=request.get_host()):
        redirect_to = settings.LOGIN_REDIRECT_URL
    response = redirect(redirect_to)
    response.set_cookie(settings.LANGUAGE_COOKIE_NAME, p.language, 10*365*24*3600)
    return response

def language(request, lang):
    cname = settings.LANGUAGE_COOKIE_NAME
    if not cname:
        cname = 'django_language'
    redirect_to = request.META['HTTP_REFERER']
    r = redirect(redirect_to)
    if not redirect_to:
        redirect_to = "/"

    try:
        p = Person.objects.get(user=request.user)
        p.language = lang
        p.save()
    except ValidationError as e:
        messages.error(e)
    except:
        messages.error(_("Could not found Person object."))
    r.set_cookie(cname, lang, 10*365*24*3600)
    return r

@login_required
def group_show(request, gid):
    user = request.user
    group = get_object_or_404(Group, id=gid)
    mytemplates = [t for t in Template.objects.filter(owner=request.user).all()]
    for i, t in enumerate(mytemplates):
        t.myshares = t.share_set.filter(group=group)
        mytemplates[i] = t
    publictemplates = [t for t in Template.objects.filter(public=True, state='READY').all()]
    for i, t in enumerate(publictemplates):
        t.myshares = t.share_set.filter(group=group)
        publictemplates[i] = t
    return render_to_response("show-group.html", RequestContext(request,{
        'group': group,
        'members': group.members.all(),
        'mytemplates': mytemplates,
        'publictemplates': publictemplates,
        }))

@login_required
def group_new(request):
    name = request.POST['name']
    semester = Semester.objects.get(id=request.POST['semester'])
    members_list = re.split('\r?\n', request.POST['members'])
    members = []
    for member in members_list:
        if re.match('^[a-zA-Z][a-zA-Z0-9]{5}$', member) == None:
            messages.error(request, _('Invalid NEPTUN code found.'))
            return redirect('/')
        person, created = Person.objects.get_or_create(code=member)
        members.append(person)
    owner = request.user.person_set.all()[0]
    group = Group()
    group.name = name
    group.semester = semester
    group.save()
    for member in members:
        group.members.add(member)
    group.owners.add(owner)
    group.save()
    return redirect('/group/show/%s' % group.id)

@login_required
def group_ajax_add_new_member(request, gid):
    group = get_object_or_404(Group, id=gid)
    member = request.POST['neptun']
    if re.match('^[a-zA-Z][a-zA-Z0-9]{5}$', member) == None:
        status = json.dumps({'status': 'Error'})
        messages.error(request, _('Invalid NEPTUN code'))
        return HttpResponse(status)
    person, created = Person.objects.get_or_create(code=member)
    group.members.add(person)
    group.save()
    return HttpResponse(json.dumps({
        'status': 'OK'
        }))

@login_required
def group_ajax_remove_member(request, gid):
    group = get_object_or_404(Group, id=gid)
    member = request.POST['neptun']
    if re.match('^[a-zA-Z][a-zA-Z0-9]{5}$', member) == None:
        status = json.dumps({'status': 'Error'})
        messages.error(request, _('Invalid NEPTUN code'))
        return HttpResponse(status)
    person, created = Person.objects.get_or_create(code=member)
    group.members.remove(person)
    group.save()
    return HttpResponse(json.dumps({
        'status': 'OK'
        }))

@login_required
def group_ajax_delete(request):
    group = get_object_or_404(Group, id=request.POST['gid'])
    group.delete()
    return HttpResponse(json.dumps({
        'status': 'OK'
        }))
