# -*- coding: utf-8 -*-

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

from django.contrib import admin
from firewall.models import (Rule, Host, Vlan, Group, VlanGroup, Firewall,
                             Domain, Record, BlacklistItem,
                             SwitchPort, EthernetDevice)
from django import contrib


class RuleInline(contrib.admin.TabularInline):
    model = Rule


class RecordInline(contrib.admin.TabularInline):
    model = Record


class HostAdmin(admin.ModelAdmin):
    list_display = ('hostname', 'vlan', 'ipv4', 'ipv6', 'external_ipv4', 'mac',
                    'shared_ip', 'owner', 'description', 'reverse',
                    'list_groups')
    ordering = ('hostname', )
    list_filter = ('owner', 'vlan', 'groups')
    search_fields = ('hostname', 'description', 'ipv4', 'ipv6', 'mac')
    filter_horizontal = ('groups', )
    inlines = (RuleInline, RecordInline)

    def queryset(self, request):
        qs = super(HostAdmin, self).queryset(request)
        return qs.prefetch_related('groups')

    @staticmethod
    def list_groups(instance):
        """Returns instance's groups' names as a comma-separated list."""
        names = [group.name for group in instance.groups.all()]
        return u', '.join(names)


class HostInline(contrib.admin.TabularInline):
    model = Host
    fields = ('hostname', 'ipv4', 'ipv6', 'external_ipv4', 'mac', 'shared_ip',
              'owner', 'reverse')


class VlanAdmin(admin.ModelAdmin):
    list_display = ('vid', 'name', 'network4', 'network6',
                    'description', 'domain', 'snat_ip', )
    search_fields = ('vid', 'name', 'network4', )
    ordering = ('vid', )
    inlines = (RuleInline, )


class RuleAdmin(admin.ModelAdmin):
    list_display = ('r_type', 'color_desc', 'owner', 'extra', 'direction',
                    'action', 'proto', 'sport', 'dport', 'nat',
                    'nat_external_port', 'used_in')
    list_filter = ('vlan', 'owner', 'direction', 'action',
                   'proto', 'nat')

    def color_desc(self, instance):
        """Returns a colorful description of the instance."""
        data = {
            'type': instance.r_type,
            'src': (instance.foreign_network.name
                    if instance.direction == '1' else instance.r_type),
            'dst': (instance.r_type if instance.direction == '1'
                    else instance.foreign_network.name),
            'para': (u'<span style="color: #00FF00;">' +
                     (('proto=%s ' % instance.proto)
                      if instance.proto else '') +
                     (('sport=%s ' % instance.sport)
                      if instance.sport else '') +
                     (('dport=%s ' % instance.dport)
                      if instance.dport else '') +
                     '</span>'),
            'desc': instance.description}
        return (u'<span style="color: #FF0000;">[%(type)s]</span> '
                u'%(src)s<span style="color: #0000FF;"> ▸ </span>%(dst)s '
                u'%(para)s %(desc)s') % data
    color_desc.allow_tags = True

    @staticmethod
    def vlan_l(instance):
        """Returns instance's VLANs' names as a comma-separated list."""
        names = [vlan.name for vlan in instance.foreign_network.vlans.all()]
        return u', '.join(names)

    @staticmethod
    def used_in(instance):
        for field in [instance.vlan, instance.vlangroup, instance.host,
                      instance.hostgroup, instance.firewall]:
            if field:
                return unicode(field) + ' ' + field._meta.object_name


class AliasAdmin(admin.ModelAdmin):
    list_display = ('alias', 'host')


class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'description')
    inlines = (RuleInline, )


class FirewallAdmin(admin.ModelAdmin):
    inlines = (RuleInline, )


class DomainAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner')


class RecordAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'address', 'ttl', 'host', 'owner')


class BlacklistItemAdmin(admin.ModelAdmin):
    list_display = ('ipv4', 'whitelisted', 'reason', 'expires_at',
                    'created_at', 'modified_at')


class SwitchPortAdmin(admin.ModelAdmin):
    list_display = ()


class EthernetDeviceAdmin(admin.ModelAdmin):
    list_display = ('name', )


admin.site.register(Host, HostAdmin)
admin.site.register(Vlan, VlanAdmin)
admin.site.register(Rule, RuleAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(VlanGroup)
admin.site.register(Firewall, FirewallAdmin)
admin.site.register(Domain, DomainAdmin)
admin.site.register(Record, RecordAdmin)
admin.site.register(BlacklistItem, BlacklistItemAdmin)
admin.site.register(SwitchPort)
admin.site.register(EthernetDevice, EthernetDeviceAdmin)
