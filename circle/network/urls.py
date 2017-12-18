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

from django.conf.urls import url
from rest_framework import routers

from . import views
from . import api_views

router = routers.DefaultRouter()
router.register(r'blacklist', api_views.BlacklistViewSet)


urlpatterns = [
    url('^$', views.IndexView.as_view(), name='network.index'),

    # blacklist
    url('^blacklist/$', views.BlacklistList.as_view(),
        name='network.blacklist_list'),
    url('^blacklist/create$', views.BlacklistCreate.as_view(),
        name='network.blacklist_create'),
    url('^blacklist/(?P<pk>\d+)/$', views.BlacklistDetail.as_view(),
        name='network.blacklist'),
    url('^blacklist/delete/(?P<pk>\d+)/$', views.BlacklistDelete.as_view(),
        name="network.blacklist_delete"),

    # domain
    url('^domains/$', views.DomainList.as_view(), name='network.domain_list'),
    url('^domains/create$', views.DomainCreate.as_view(),
        name='network.domain_create'),
    url('^domains/(?P<pk>\d+)/$', views.DomainDetail.as_view(),
        name='network.domain'),
    url('^domains/delete/(?P<pk>\d+)/$', views.DomainDelete.as_view(),
        name="network.domain_delete"),

    # firewall
    url('^firewalls/$', views.FirewallList.as_view(),
        name='network.firewall_list'),
    url('^firewalls/create$', views.FirewallCreate.as_view(),
        name='network.firewall_create'),
    url('^firewalls/(?P<pk>\d+)/$', views.FirewallDetail.as_view(),
        name='network.firewall'),
    url('^firewalls/delete/(?P<pk>\d+)/$', views.FirewallDelete.as_view(),
        name="network.firewall_delete"),

    # group (host)
    url('^groups/$', views.GroupList.as_view(), name='network.group_list'),
    url('^groups/create$', views.GroupCreate.as_view(),
        name='network.group_create'),
    url('^groups/(?P<pk>\d+)/$', views.GroupDetail.as_view(), name='network.group'),
    url('^groups/delete/(?P<pk>\d+)/$', views.GroupDelete.as_view(),
        name="network.group_delete"),

    # host
    url('^hosts/$', views.HostList.as_view(), name='network.host_list'),
    url('^hosts/create$', views.HostCreate.as_view(), name='network.host_create'),
    url('^hosts/(?P<pk>\d+)/$', views.HostDetail.as_view(), name='network.host'),
    url('^hosts/delete/(?P<pk>\d+)/$', views.HostDelete.as_view(),
        name="network.host_delete"),

    # record
    url('^records/$', views.RecordList.as_view(), name='network.record_list'),
    url('^records/create$', views.RecordCreate.as_view(),
        name='network.record_create'),
    url('^records/(?P<pk>\d+)/$', views.RecordDetail.as_view(),
        name='network.record'),
    url('^records/delete/(?P<pk>\d+)/$', views.RecordDelete.as_view(),
        name="network.record_delete"),

    # rule
    url('^rules/$', views.RuleList.as_view(), name='network.rule_list'),
    url('^rules/create$', views.RuleCreate.as_view(), name='network.rule_create'),
    url('^rules/(?P<pk>\d+)/$', views.RuleDetail.as_view(),
        name='network.rule'),

    # switchport
    url('^switchports/$', views.SwitchPortList.as_view(),
        name='network.switch_port_list'),
    url('^switchports/create$', views.SwitchPortCreate.as_view(),
        name='network.switch_port_create'),
    url('^switchports/(?P<pk>\d+)/$', views.SwitchPortDetail.as_view(),
        name='network.switch_port'),
    url('^switchports/delete/(?P<pk>\d+)/$', views.SwitchPortDelete.as_view(),
        name="network.switch_port_delete"),

    # vlan
    url('^vlans/$', views.VlanList.as_view(), name='network.vlan_list'),
    url('^vlans/create$', views.VlanCreate.as_view(), name='network.vlan_create'),
    url('^vlans/(?P<vid>\d+)/$', views.VlanDetail.as_view(), name='network.vlan'),
    url('^vlans/(?P<pk>\d+)/acl/$', views.VlanAclUpdateView.as_view(),
        name='network.vlan-acl'),
    url('^vlans/delete/(?P<vid>\d+)/$', views.VlanDelete.as_view(),
        name="network.vlan_delete"),

    # vlangroup
    url('^vlangroups/$', views.VlanGroupList.as_view(),
        name='network.vlan_group_list'),
    url('^vlangroups/create$', views.VlanGroupCreate.as_view(),
        name='network.vlan_group_create'),
    url('^vlangroups/(?P<pk>\d+)/$', views.VlanGroupDetail.as_view(),
        name='network.vlan_group'),
    url('^vlangroups/delete/(?P<pk>\d+)/$', views.VlanGroupDelete.as_view(),
        name="network.vlan_group_delete"),
    url('^rules/delete/(?P<pk>\d+)/$', views.RuleDelete.as_view(),
        name="network.rule_delete"),

    # non class based views
    url('^hosts/(?P<pk>\d+)/remove/(?P<group_pk>\d+)/$', views.remove_host_group,
        name='network.remove_host_group'),
    url('^hosts/(?P<pk>\d+)/add/$', views.add_host_group,
        name='network.add_host_group'),
    url('^switchports/(?P<pk>\d+)/remove/(?P<device_pk>\d+)/$',
        views.remove_switch_port_device, name='network.remove_switch_port_device'),
    url('^switchports/(?P<pk>\d+)/add/$', views.add_switch_port_device,
        name='network.add_switch_port_device'),
]
