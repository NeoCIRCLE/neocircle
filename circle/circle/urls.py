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

from django.conf.urls import include, url
from django.views.generic import TemplateView

from django.conf import settings
from django.contrib import admin
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.contrib.auth.views import (
    password_reset_confirm, password_reset
)


from circle.settings.base import get_env_variable
from dashboard.views import (
    CircleLoginView, HelpView, ResizeHelpView, TwoFactorLoginView
)
from dashboard.forms import CirclePasswordResetForm, CircleSetPasswordForm
from firewall.views import add_blacklist_item


admin.autodiscover()

urlpatterns = [
    url(r'^$', lambda x: redirect(reverse("dashboard.index"))),
    url(r'^network/', include('network.urls')),
    url(r'^blacklist-add/', add_blacklist_item),
    url(r'^dashboard/', include('dashboard.urls')),
    url(r'^request/', include('request.urls')),

    # django/contrib/auth/urls.py (care when new version)
    url((r'^accounts/reset/(?P<uidb64>[0-9A-Za-z_\-]+)/'
         r'(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$'),
        password_reset_confirm,
        {'set_password_form': CircleSetPasswordForm},
        name='accounts.password_reset_confirm'
        ),
    url(r'^accounts/password/reset/$', password_reset,
        {'password_reset_form': CirclePasswordResetForm},
        name="accounts.password-reset",
        ),
    url(r'^accounts/login/?$', CircleLoginView.as_view(),
        name="accounts.login"),
    url(r'^accounts/', include('django.contrib.auth.urls')),
    url(r'^two-factor-login/$', TwoFactorLoginView.as_view(),
        name="two-factor-login"),

    url(r'^info/help/$', HelpView.as_view(template_name="info/help.html"),
        name="info.help"),
    url(r'^info/policy/$',
        TemplateView.as_view(template_name="info/policy.html"),
        name="info.policy"),
    url(r'^info/legal/$',
        TemplateView.as_view(template_name="info/legal.html"),
        name="info.legal"),
    url(r'^info/support/$',
        TemplateView.as_view(template_name="info/support.html"),
        name="info.support"),
    url(r'^info/resize-how-to/$', ResizeHelpView.as_view(),
        name="info.resize"),

    # API urls
    url(r'api/v1/network/', include('network.api_urls')),
    url(r'api/v1/dashboard/', include('dashboard.api_urls')),
]


if 'rosetta' in settings.INSTALLED_APPS:
    urlpatterns += [
        url(r'^rosetta/', include('rosetta.urls')),
    ]

if settings.ADMIN_ENABLED:
    urlpatterns += [
        url(r'^admin/', include(admin.site.urls)),
    ]


if get_env_variable('DJANGO_SAML', 'FALSE') == 'TRUE':
    urlpatterns += [
        url(r'^saml2/', include('djangosaml2.urls')),
    ]

handler500 = 'common.views.handler500'
handler403 = 'common.views.handler403'
