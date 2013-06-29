from datetime import datetime
from itertools import chain
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group as AGroup
from django.contrib import messages
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import mail_managers, send_mail
from django.core.urlresolvers import reverse
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
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import *
from django.views.generic import *
from one.models import *
from school.models import *
import django.contrib.auth as auth
import logging
import json
import re

logger = logging.getLogger(__name__)


neptun_re = re.compile('^[a-zA-Z][a-zA-Z0-9]{5}$')

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
    try:
        user.email = request.META['email']
    except KeyError:
        messages.error(request, _("The identity provider did not pass the mandatory e-mail data."))
        raise PermissionDenied()
    user.save()
    p, created = Person.objects.get_or_create(code=user.username)
    p.user_id = user.id
    p.save()

    sem = Semester.get_current()

    attended = request.META['niifEduPersonAttendedCourse']
    attended = [c for c in attended.split(';') if c != '']
    for c in attended:
        try:
            co = Course.objects.get(code=c)
        except Course.DoesNotExist as e:
            logger.warning("Django could not get Course %s: %s" % (c, e))
            continue
        g = co.get_or_create_default_group()
        if p.course_groups.filter(semester=sem, course=co).count() == 0:
            try:
                g.members.add(p)
                g.save()
                messages.info(request,
                        _('Course "%s" added.') % g.course)
                logger.info('Django Course "%s" added.' % g.course)
            except Exception as e:
                messages.error(request,
                        _('Failed to add course "%s".') % g.course)
                logger.warning("Django ex %s" % e)

    held = request.META['niifEduPersonHeldCourse']
    held = [c for c in held.split(';') if c != '']
    for c in held:
        co, created = Course.objects.get_or_create(code=c)
        if created:
            logger.info("Django Course %s created" % c)
        g = co.get_or_create_default_group()
        try:
            co.owners.add(p)
            g.owners.add(p)
            messages.info(request,
                    _('Course "%s" ownership added.') % g.course)
        except Exception as e:
            messages.error(request,
                    _('Failed to add course "%s" ownership.') % g.course)
            logger.warning("Django ex %s" % e)
        co.save()
        g.save()

    try:
        affiliation = request.META['affiliation']
    except KeyError:
        affiliation = ''

    affiliation = [a for a in affiliation.split(';') if a != '']
    for a in affiliation:
        g, created = AGroup.objects.get_or_create(name=a)
        user.groups.add(g)
        try:
            g = Group.objects.get(name=a)
            g.members.add(p)
            g.save()
            logger.info("Django affiliation group %s added to %s" % (a, p))
        except Exception as e:
            logger.warning("Django FAILed to add affiliation group %s to %s."
                    " Reason: %s" % (a, p, e))
    user.save()

    p.save()
    user.backend = 'django.contrib.auth.backends.ModelBackend'
    auth.login(request, user)
    logger.info("Shibboleth login with %s" % request.META)

    redirect_to = request.REQUEST.get(auth.REDIRECT_FIELD_NAME, '')
    if not is_safe_url(url=redirect_to, host=request.get_host()):
        redirect_to = settings.LOGIN_REDIRECT_URL
    response = redirect(redirect_to)
    response.set_cookie(
        settings.LANGUAGE_COOKIE_NAME, p.language, 10 * 365 * 24 * 3600)
    return response


def language(request, lang):
    try:
        p = Person.objects.get(user=request.user)
        p.language = lang
        p.save()
    except ValidationError as e:  # couldn't test this case
        messages.error(request, e)
    except Person.DoesNotExist:
        messages.error(request, _("Could not find Person object."))

    cname = settings.LANGUAGE_COOKIE_NAME or 'django_language'
    redirect_to = request.META['HTTP_REFERER']
    r = redirect(redirect_to)
    r.set_cookie(cname, lang, 10 * 365 * 24 * 3600)
    return r


@login_required
def group_show(request, gid):
    user = request.user
    group = get_object_or_404(Group, id=gid)

    mytemplates = Template.objects.filter(owner=request.user, state='READY')
    for t in mytemplates:
        t.myshares = t.share_set.filter(group=group)

    publictemplates = Template.objects.filter(public=True, state='READY')
    for t in publictemplates:
        t.myshares = t.share_set.filter(group=group)

    all_templates = chain(mytemplates, publictemplates)
    has_share = any([t.myshares.exists() for t in all_templates])

    return render_to_response("show-group.html", RequestContext(request, {
        'group': group,
        'members': group.members.all(),
        'mytemplates': mytemplates,
        'publictemplates': publictemplates,
        'noshare': not has_share,
        'userdetails': UserCloudDetails.objects.get(user=request.user),
        'owners': group.owners.all(),
    }))


@login_required
def group_new(request):
    name = request.POST['name']
    semester = Semester.objects.get(id=request.POST['semester'])
    members_list = re.split('\r?\n', request.POST['members'])
    members_list = [m for m in members_list if m != '']
    members = []
    for member in members_list:
        if neptun_re.match(member.strip()) is None:
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
    url = reverse('school.views.group_show', kwargs={'gid': group.id})
    return redirect(url)


@login_required
def group_ajax_add_new_member(request, gid):
    group = get_object_or_404(Group, id=gid)
    member = request.POST['neptun']
    if neptun_re.match(member.strip()) is None:
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
    if neptun_re.match(member.strip()) is None:
        status = json.dumps({'status': 'Error'})
        messages.error(request, _('Invalid NEPTUN code'))
        return HttpResponse(status)
    person = Person.objects.get(code=member)
    group.members.remove(person)
    group.save()
    return HttpResponse(json.dumps({
        'status': 'OK'
    }))


@login_required
def group_ajax_delete(request):
    # TODO should take parameter in URL using DELETE command
    gid = request.POST['gid']
    group = get_object_or_404(Group, id=gid)
    group.delete()
    return HttpResponse(json.dumps({
        'status': 'OK'
    }))


@login_required
def group_ajax_owner_autocomplete(request):
    # TODO should be renamed to something like 'user_ajax_autocomplete'
    query = request.POST['q']
    users = chain(User.objects.filter(last_name__istartswith=query)[:5],
                  User.objects.filter(first_name__istartswith=query)[:5],
                  User.objects.filter(username__istartswith=query)[:5])
    results = [{'name': user.get_full_name(),
                'neptun': user.username} for user in users]
    return HttpResponse(json.dumps(results, ensure_ascii=False))


@login_required
def group_ajax_add_new_owner(request, gid):
    if request.user.cloud_details.share_quota <= 0:
        return HttpResponse(json.dumps({'status': 'denied'}))
    group = get_object_or_404(Group, id=gid)
    member = request.POST['neptun']
    if neptun_re.match(member.strip()) is None:
        status = json.dumps({'status': 'Error'})
        messages.error(request, _('Invalid NEPTUN code'))
        return HttpResponse(status)
    person, created = Person.objects.get_or_create(code=member)
    group.owners.add(person)
    group.save()
    return HttpResponse(json.dumps({'status': 'OK'}))
