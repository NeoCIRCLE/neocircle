from django.conf.urls import patterns, url

from .views import IndexView, HostList, HostDetail


urlpatterns = patterns(
    '',
    url('^$', IndexView.as_view(), name='network.index'),
    url('^hosts/$', HostList.as_view(), name='network.host_list'),
    url('^hosts/(?P<pk>\d+)/$', HostDetail.as_view(), name='network.host'),
)
