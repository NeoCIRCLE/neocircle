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
from django.utils.http import is_safe_url
from django.utils.translation import get_language as lang
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import *
from django.views.generic import *
from one.models import *
import django.contrib.auth as auth
import logging

logger = logging.getLogger(__name__)


SHIB_ATTRIBUTE_MAP = {
    "HTTP_SHIB_IDENTITY_PROVIDER": (True, "idp"),
    "email": (True, "email"),
    "sn": (True, "sn"),
    "givenName": (True, "givenName"),
    "niifPersonOrgID": (True, "niifPersonOrgID"),
}


def parse_attributes(META):
    shib_attrs = {}
    error = False
    for header, attr in SHIB_ATTRIBUTE_MAP.items():
        required, name = attr
        values = META.get(header, None)
        value = None
        if values:
            # If multiple attributes releases just care about the 1st one
            try:
                value = values.split(';')[0]
            except:
                value = values
                
        shib_attrs[name] = value
        if not value or value == '':
            if required:
                error = True
    return shib_attrs, error

def logout(request):
    auth.logout(request)
    return redirect('/Shibboleth.sso/Logout?return=https%3a%2f%2fcloud.ik.bme.hu%2f')


def login(request):
    attr, error = parse_attributes(request.META)
    if not attr['niifPersonOrgID']:
        messages.error(request, _('EduID is not available.'))
	return redirect('/admin')
    try:
        user = User.objects.get(username=attr['niifPersonOrgID'])
    except User.DoesNotExist:
        user = User(username=attr['niifPersonOrgID'])
    user.set_unusable_password()
    user.first_name = attr['givenName']
    user.last_name = attr['sn']
    user.email = attr['email']
    user.save()

    user.backend = 'django.contrib.auth.backends.ModelBackend'
    auth.login(request, user)
    logger.warning("Shib login with %s" % request.META)

    redirect_to = request.REQUEST.get(auth.redirect_field_name, '')
    if not is_safe_url(url=redirect_to, host=request.get_host()):
        redirect_to = settings.LOGIN_REDIRECT_URL
    return redirect('/')
