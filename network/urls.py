from django.conf.urls import patterns, url

from .views import (IndexView, HostList, HostDetail, VlanList, VlanDetail,
                    DomainList, DomainDetail, GroupList, GroupDetail,
                    RecordList, RecordDetail, BlacklistList, BlacklistDetail)


urlpatterns = patterns(
    '',
    url('^$', IndexView.as_view(), name='network.index'),
    url('^blacklists/$', BlacklistList.as_view(),
        name='network.blacklist_list'),
    url('^blacklists/(?P<pk>\d+)/$', BlacklistDetail.as_view(),
        name='network.blacklist'),
    url('^domains/$', DomainList.as_view(), name='network.domain_list'),
    url('^domains/(?P<pk>\d+)/$', DomainDetail.as_view(),
        name='network.domain'),
    url('^groups/$', GroupList.as_view(), name='network.group_list'),
    url('^groups/(?P<pk>\d+)/$', GroupDetail.as_view(), name='network.group'),
    url('^hosts/$', HostList.as_view(), name='network.host_list'),
    url('^hosts/(?P<pk>\d+)/$', HostDetail.as_view(), name='network.host'),
    url('^records/$', RecordList.as_view(), name='network.record_list'),
    url('^records/(?P<pk>\d+)/$', RecordDetail.as_view(),
        name='network.record'),
    url('^vlans/$', VlanList.as_view(), name='network.vlan_list'),
    url('^vlans/(?P<vid>\d+)/$', VlanDetail.as_view(), name='network.vlan'),
)
