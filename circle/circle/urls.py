from django.conf.urls import patterns, include, url
# from django.views.generic import TemplateView

from django.contrib import admin

from circle.settings.base import get_env_variable

admin.autodiscover()

urlpatterns = patterns(
    '',
    #url(r'^$', TemplateView.as_view(template_name='base.html')),

    # Examples:
    # url(r'^$', 'circle.views.home', name='home'),
    # url(r'^circle/', include('circle.foo.urls')),

    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^network/', include('network.urls')),
    url(r'^dashboard/', include('dashboard.urls')),
    url(r'^accounts/', include('django.contrib.auth.urls')),
)


if get_env_variable('DJANGO_SAML', 'FALSE') == 'TRUE':
    urlpatterns += patterns(
        '',
        (r'^saml2/', include('djangosaml2.urls')),
    )
