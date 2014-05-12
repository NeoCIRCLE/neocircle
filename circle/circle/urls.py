# Copyright 2014 Budapest University of Technology and Economics (BME IK)
#
# This file is part of CIRCLE Cloud.
#
# CIRCLE is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# CIRCLE is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along
# with CIRCLE.  If not, see <http://www.gnu.org/licenses/>.

from django.conf.urls import patterns, include, url
# from django.views.generic import TemplateView

from django.contrib import admin
from django.shortcuts import redirect
from django.core.urlresolvers import reverse

from circle.settings.base import get_env_variable
from dashboard.views import circle_login
from dashboard.forms import CirclePasswordResetForm, CircleSetPasswordForm

admin.autodiscover()

urlpatterns = patterns(
    '',
    #url(r'^$', TemplateView.as_view(template_name='base.html')),

    # Examples:
    # url(r'^$', 'circle.views.home', name='home'),
    # url(r'^circle/', include('circle.foo.urls')),

    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    url(r'^$', lambda x: redirect(reverse("dashboard.index"))),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^network/', include('network.urls')),
    url(r'^dashboard/', include('dashboard.urls')),
    url(r'^occi/', include('occi.urls')),

    url((r'^accounts/reset/(?P<uidb36>[0-9A-Za-z]{1,13})-'
         '(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$'),
        'django.contrib.auth.views.password_reset_confirm',
        {'set_password_form': CircleSetPasswordForm},
        name='accounts.password_reset_confirm'
        ),
    url(r'^accounts/password/reset/$', ("django.contrib.auth.views."
                                        "password_reset"),
        {'password_reset_form': CirclePasswordResetForm},
        name="accounts.password-reset",
        ),
    url(r'^accounts/login/?$', circle_login, name="accounts.login"),
    url(r'^accounts/', include('django.contrib.auth.urls')),
)


if get_env_variable('DJANGO_SAML', 'FALSE') == 'TRUE':
    urlpatterns += patterns(
        '',
        (r'^saml2/', include('djangosaml2.urls')),
    )
