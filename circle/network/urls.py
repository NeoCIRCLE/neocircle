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
from .views import (
    IndexView,
    HostList, HostDetail, HostCreate, HostDelete,
    VlanList, VlanDetail, VlanDelete, VlanCreate,
    DomainList, DomainDetail, DomainDelete, DomainCreate,
    GroupList, GroupDetail, GroupDelete, GroupCreate,
    RecordList, RecordDetail, RecordCreate, RecordDelete,
    BlacklistList, BlacklistDetail, BlacklistDelete, BlacklistCreate,
    RuleList, RuleDetail, RuleDelete, RuleCreate,
    SwitchPortList, SwitchPortDetail, SwitchPortCreate, SwitchPortDelete,
    VlanGroupList, VlanGroupDetail, VlanGroupDelete, VlanGroupCreate,
    FirewallList, FirewallDetail, FirewallCreate, FirewallDelete,
    remove_host_group, add_host_group,
    remove_switch_port_device, add_switch_port_device,
    VlanAclUpdateView
)

urlpatterns = [
    url('^$', IndexView.as_view(), name='network.index'),
    # blacklist
    url('^blacklist/$', BlacklistList.as_view(),
        name='network.blacklist_list'),
    url('^blacklist/create$', BlacklistCreate.as_view(),
        name='network.blacklist_create'),
    url('^blacklist/(?P<pk>\d+)/$', BlacklistDetail.as_view(),
        name='network.blacklist'),
    url('^blacklist/delete/(?P<pk>\d+)/$', BlacklistDelete.as_view(),
        name="network.blacklist_delete"),

    # domain
    url('^domains/$', DomainList.as_view(), name='network.domain_list'),
    url('^domains/create$', DomainCreate.as_view(),
        name='network.domain_create'),
    url('^domains/(?P<pk>\d+)/$', DomainDetail.as_view(),
        name='network.domain'),
    url('^domains/delete/(?P<pk>\d+)/$', DomainDelete.as_view(),
        name="network.domain_delete"),

    # firewall
    url('^firewalls/$', FirewallList.as_view(),
        name='network.firewall_list'),
    url('^firewalls/create$', FirewallCreate.as_view(),
        name='network.firewall_create'),
    url('^firewalls/(?P<pk>\d+)/$', FirewallDetail.as_view(),
        name='network.firewall'),
    url('^firewalls/delete/(?P<pk>\d+)/$', FirewallDelete.as_view(),
        name="network.firewall_delete"),

    # group (host)
    url('^groups/$', GroupList.as_view(), name='network.group_list'),
    url('^groups/create$', GroupCreate.as_view(),
        name='network.group_create'),
    url('^groups/(?P<pk>\d+)/$', GroupDetail.as_view(), name='network.group'),
    url('^groups/delete/(?P<pk>\d+)/$', GroupDelete.as_view(),
        name="network.group_delete"),

    # host
    url('^hosts/$', HostList.as_view(), name='network.host_list'),
    url('^hosts/create$', HostCreate.as_view(), name='network.host_create'),
    url('^hosts/(?P<pk>\d+)/$', HostDetail.as_view(), name='network.host'),
    url('^hosts/delete/(?P<pk>\d+)/$', HostDelete.as_view(),
        name="network.host_delete"),

    # record
    url('^records/$', RecordList.as_view(), name='network.record_list'),
    url('^records/create$', RecordCreate.as_view(),
        name='network.record_create'),
    url('^records/(?P<pk>\d+)/$', RecordDetail.as_view(),
        name='network.record'),
    url('^records/delete/(?P<pk>\d+)/$', RecordDelete.as_view(),
        name="network.record_delete"),

    # rule
    url('^rules/$', RuleList.as_view(), name='network.rule_list'),
    url('^rules/create$', RuleCreate.as_view(), name='network.rule_create'),
    url('^rules/(?P<pk>\d+)/$', RuleDetail.as_view(),
        name='network.rule'),

    # switchport
    url('^switchports/$', SwitchPortList.as_view(),
        name='network.switch_port_list'),
    url('^switchports/create$', SwitchPortCreate.as_view(),
        name='network.switch_port_create'),
    url('^switchports/(?P<pk>\d+)/$', SwitchPortDetail.as_view(),
        name='network.switch_port'),
    url('^switchports/delete/(?P<pk>\d+)/$', SwitchPortDelete.as_view(),
        name="network.switch_port_delete"),

    # vlan
    url('^vlans/$', VlanList.as_view(), name='network.vlan_list'),
    url('^vlans/create$', VlanCreate.as_view(), name='network.vlan_create'),
    url('^vlans/(?P<vid>\d+)/$', VlanDetail.as_view(), name='network.vlan'),
    url('^vlans/(?P<pk>\d+)/acl/$', VlanAclUpdateView.as_view(),
        name='network.vlan-acl'),
    url('^vlans/delete/(?P<vid>\d+)/$', VlanDelete.as_view(),
        name="network.vlan_delete"),

    # vlangroup
    url('^vlangroups/$', VlanGroupList.as_view(),
        name='network.vlan_group_list'),
    url('^vlangroups/create$', VlanGroupCreate.as_view(),
        name='network.vlan_group_create'),
    url('^vlangroups/(?P<pk>\d+)/$', VlanGroupDetail.as_view(),
        name='network.vlan_group'),
    url('^vlangroups/delete/(?P<pk>\d+)/$', VlanGroupDelete.as_view(),
        name="network.vlan_group_delete"),
    url('^rules/delete/(?P<pk>\d+)/$', RuleDelete.as_view(),
        name="network.rule_delete"),

    # non class based views
    url('^hosts/(?P<pk>\d+)/remove/(?P<group_pk>\d+)/$', remove_host_group,
        name='network.remove_host_group'),
    url('^hosts/(?P<pk>\d+)/add/$', add_host_group,
        name='network.add_host_group'),
    url('^switchports/(?P<pk>\d+)/remove/(?P<device_pk>\d+)/$',
        remove_switch_port_device, name='network.remove_switch_port_device'),
    url('^switchports/(?P<pk>\d+)/add/$', add_switch_port_device,
        name='network.add_switch_port_device'),
]
