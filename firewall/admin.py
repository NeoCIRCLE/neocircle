# -*- coding: utf8 -*-

from django.contrib import admin
from firewall.models import *
from django import contrib


class AliasInline(contrib.admin.TabularInline):
    model = Alias

class RuleInline(contrib.admin.TabularInline):
    model = Rule

class HostAdmin(admin.ModelAdmin):
    list_display = ('hostname', 'vlan', 'ipv4', 'ipv6', 'pub_ipv4', 'mac',
        'shared_ip', 'owner', 'description', 'reverse', 'groups_l')
    ordering = ('hostname', )
    list_filter = ('owner', 'vlan', 'groups')
    search_fields = ('hostname', 'description', 'ipv4', 'ipv6', 'mac')
    filter_horizontal = ('groups', )
    inlines = (AliasInline, RuleInline)

    def groups_l(self, instance):
        retval = []
        for i in instance.groups.all():
            retval.append(i.name)
        return u', '.join(retval)

class HostInline(contrib.admin.TabularInline):
    model = Host
    fields = ('hostname', 'ipv4', 'ipv6', 'pub_ipv4', 'mac', 'shared_ip',
        'owner', 'reverse')

class VlanAdmin(admin.ModelAdmin):
    list_display = ('vid', 'name', 'ipv4', 'net_ipv4', 'ipv6', 'net_ipv6',
        'description', 'domain', 'snat_ip', )
    ordering = ('vid', )
    inlines = (RuleInline, )

class RuleAdmin(admin.ModelAdmin):
    list_display = ('r_type', 'color_desc', 'owner', 'extra', 'direction',
        'accept', 'proto', 'sport', 'dport', 'nat', 'nat_dport', 'used_in')
    list_filter = ('r_type', 'vlan', 'owner', 'direction', 'accept',
        'proto', 'nat')

    def color_desc(self, instance):
        para = '</span>'
        if(instance.dport):
            para = "dport=%s %s" % (instance.dport, para)
        if(instance.sport):
            para = "sport=%s %s" % (instance.sport, para)
        if(instance.proto):
            para = "proto=%s %s" % (instance.proto, para)
        para= u'<span style="color: #00FF00;">' + para
        return u'<span style="color: #FF0000;">[' + instance.r_type + u']</span> ' + (instance.foreign_network.name + u'<span style="color: #0000FF;"> ▸ </span>' + instance.r_type if instance.direction=='1' else instance.r_type + u'<span style="color: #0000FF;"> ▸ </span>' + instance.foreign_network.name) + ' ' + para + ' ' + instance.description
    color_desc.allow_tags = True

    def vlan_l(self, instance):
        retval = []
        for vl in instance.foreign_network.vlans.all():
            retval.append(vl.name)
        return u', '.join(retval)

    def used_in(self, instance):
        for field in [instance.vlan, instance.vlangroup, instance.host, instance.hostgroup, instance.firewall]:
            if field is not None:
                return unicode(field) + ' ' + field._meta.object_name


class AliasAdmin(admin.ModelAdmin):
    list_display = ('alias', 'host')

class SettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'description')

class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'description')
    inlines = (RuleInline, )

class FirewallAdmin(admin.ModelAdmin):
    inlines = (RuleInline, )

admin.site.register(Host, HostAdmin)
admin.site.register(Vlan, VlanAdmin)
admin.site.register(Rule, RuleAdmin)
admin.site.register(Alias, AliasAdmin)
admin.site.register(Setting, SettingAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(VlanGroup)
admin.site.register(Firewall, FirewallAdmin)
