from django.conf.urls import patterns, url

from .views import IndexView, HostList, HostDetail


urlpatterns = patterns(
    '',
    url('^$', IndexView.as_view(), name='network.index'),
)
