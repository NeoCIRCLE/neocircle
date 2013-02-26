# -*- coding: utf8 -*-

from django.contrib import admin
from firewall.models import *
from django import contrib


class RuleInline(contrib.admin.TabularInline):
    model = Rule

class RecordInline(contrib.admin.TabularInline):
    model = Record

class HostAdmin(admin.ModelAdmin):
    list_display = ('hostname', 'vlan', 'ipv4', 'ipv6', 'pub_ipv4', 'mac',
        'shared_ip', 'owner', 'description', 'reverse', 'list_groups')
    ordering = ('hostname', )
    list_filter = ('owner', 'vlan', 'groups')
    search_fields = ('hostname', 'description', 'ipv4', 'ipv6', 'mac')
    filter_horizontal = ('groups', )
    inlines = (RuleInline, RecordInline)

    @staticmethod
    def list_groups(instance):
        """Returns instance's groups' names as a comma-separated list."""
        names = [group.name for group in instance.groups.all()]
        return u', '.join(names)

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

    @staticmethod
    def color_desc(instance):
        """Returns a colorful description of the instance."""
        return (u'<span style="color: #FF0000;">[%(type)s]</span> '
                u'%(src)s<span style="color: #0000FF;"> ▸ </span>%(dst)s '
                u'%(para)s %(desc)s') % {
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
    list_display = ('name_', 'type', 'address_', 'ttl', 'host', 'owner')

    @staticmethod
    def address_(instance):
        a = instance.get_data()
        return a['address'] if a else None

    @staticmethod
    def name_(instance):
        a = instance.get_data()
        return a['name'] if a else None

class BlacklistAdmin(admin.ModelAdmin):
    list_display = ('ipv4', 'reason', 'created_at', 'modified_at')

admin.site.register(Host, HostAdmin)
admin.site.register(Vlan, VlanAdmin)
admin.site.register(Rule, RuleAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(VlanGroup)
admin.site.register(Firewall, FirewallAdmin)
admin.site.register(Domain, DomainAdmin)
admin.site.register(Record, RecordAdmin)
admin.site.register(Blacklist, BlacklistAdmin)

