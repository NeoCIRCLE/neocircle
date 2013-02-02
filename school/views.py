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
import django.contrib.auth as auth
import logging

logger = logging.getLogger(__name__)

def logout(request):
    auth.logout(request)
    return redirect('/Shibboleth.sso/Logout?return=https%3a%2f%2fcloud.ik.bme.hu%2f')

def login(request):
    try:
        user = User.objects.get(username=request.META['niifPersonOrgID'])
    except KeyError:
        messages.error(request, _('EduID is not available.'))
        return redirect('/admin')
    except User.DoesNotExist:
        user = User(username=attr['niifPersonOrgID'])
        user.set_unusable_password()
    user.first_name = request.META['givenName']
    user.last_name = request.META['sn']
    user.email = attr['email']
    user.save()

    user.backend = 'django.contrib.auth.backends.ModelBackend'
    auth.login(request, user)
    logger.warning("Shib login with %s" % request.META)


    redirect_to = request.REQUEST.get(auth.REDIRECT_FIELD_NAME, '')
    if not is_safe_url(url=redirect_to, host=request.get_host()):
        redirect_to = settings.LOGIN_REDIRECT_URL
    return redirect(redirect_to)
