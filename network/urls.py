from django.conf.urls import patterns, url

from .views import IndexView, HostList, HostDetail, VlanList, VlanDetail


urlpatterns = patterns(
    '',
    url('^$', IndexView.as_view(), name='network.index'),
    url('^hosts/$', HostList.as_view(), name='network.host_list'),
    url('^hosts/(?P<pk>\d+)/$', HostDetail.as_view(), name='network.host'),
    url('^vlans/$', VlanList.as_view(), name='network.vlan_list'),
    url('^vlans/(?P<pk>\d+)/$', VlanDetail.as_view(), name='network.vlan'),
)
