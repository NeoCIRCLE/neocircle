from django.conf.urls import patterns, url

from .views import (IndexView,
                    HostList, HostDetail, HostCreate, HostDelete,
                    VlanList, VlanDetail, VlanDelete,
                    DomainList, DomainDetail, DomainDelete,
                    GroupList, GroupDetail, GroupDelete,
                    RecordList, RecordDetail, RecordCreate, RecordDelete,
                    BlacklistList, BlacklistDetail, BlacklistDelete,
                    RuleList, RuleDetail, RuleDelete,
                    VlanGroupList, VlanGroupDetail, VlanGroupDelete,
                    remove_host_group, add_host_group)

js_info_dict = {
    'packages': ('network', ),
}

urlpatterns = patterns(
    '',
    url('^$', IndexView.as_view(), name='network.index'),
    url('^blacklists/$', BlacklistList.as_view(),
        name='network.blacklist_list'),
    url('^blacklists/(?P<pk>\d+)/$', BlacklistDetail.as_view(),
        name='network.blacklist'),
    url('^blacklists/delete/(?P<pk>\d+)/$', BlacklistDelete.as_view(),
        name="network.blacklist_delete"),
    url('^domains/$', DomainList.as_view(), name='network.domain_list'),
    url('^domains/(?P<pk>\d+)/$', DomainDetail.as_view(),
        name='network.domain'),
    url('^domains/delete/(?P<pk>\d+)/$', DomainDelete.as_view(),
        name="network.domain_delete"),
    url('^groups/$', GroupList.as_view(), name='network.group_list'),
    url('^groups/(?P<pk>\d+)/$', GroupDetail.as_view(), name='network.group'),
    url('^groups/delete/(?P<pk>\d+)/$', GroupDelete.as_view(),
        name="network.group_delete"),
    url('^hosts/$', HostList.as_view(), name='network.host_list'),
    url('^hosts/create$', HostCreate.as_view(), name='network.host_create'),
    url('^hosts/(?P<pk>\d+)/$', HostDetail.as_view(), name='network.host'),
    url('^hosts/delete/(?P<pk>\d+)/$', HostDelete.as_view(),
        name="network.host_delete"),
    url('^records/$', RecordList.as_view(), name='network.record_list'),
    url('^records/create$', RecordCreate.as_view(),
        name='network.record_create'),
    url('^records/(?P<pk>\d+)/$', RecordDetail.as_view(),
        name='network.record'),
    url('^records/delete/(?P<pk>\d+)/$', RecordDelete.as_view(),
        name="network.record_delete"),
    url('^rules/$', RuleList.as_view(), name='network.rule_list'),
    url('^rules/(?P<pk>\d+)/$', RuleDetail.as_view(),
        name='network.rule'),
    url('^vlans/$', VlanList.as_view(), name='network.vlan_list'),
    url('^vlans/(?P<vid>\d+)/$', VlanDetail.as_view(), name='network.vlan'),
    url('^vlans/delete/(?P<vid>\d+)/$', VlanDelete.as_view(),
        name="network.vlan_delete"),
    url('^vlangroups/$', VlanGroupList.as_view(),
        name='network.vlan_group_list'),
    url('^vlangroups/(?P<pk>\d+)/$', VlanGroupDetail.as_view(),
        name='network.vlan_group'),
    url('^vlangroups/delete/(?P<pk>\d+)/$', VlanGroupDelete.as_view(),
        name="network.vlangroup_delete"),
    url('^rules/delete/(?P<pk>\d+)/$', RuleDelete.as_view(),
        name="network.rule_delete"),
    url('^hosts/(?P<pk>\d+)/remove/(?P<group_pk>\d+)/$', remove_host_group,
        name='network.remove_host_group'),
    url('^hosts/(?P<pk>\d+)/add/$', add_host_group,
        name='network.add_host_group'),
    url(r'^jsi18n/$', 'django.views.i18n.javascript_catalog', js_info_dict,
        name="network.js_catalog"),
)
