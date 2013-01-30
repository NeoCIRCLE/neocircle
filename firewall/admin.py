from django.contrib import admin
from firewall.models import *
from django import contrib


class AliasInline(contrib.admin.TabularInline):
    model = Alias

class HostAdmin(admin.ModelAdmin):
    list_display = ('hostname', 'vlan', 'ipv4', 'ipv6', 'pub_ipv4', 'mac',
        'shared_ip', 'owner', 'groups_l', 'rules_l', 'description',
        'reverse')
    ordering = ('hostname', )
    list_filter = ('owner', 'vlan', 'groups')
    search_fields = ('hostname', 'description', 'ipv4', 'ipv6', 'mac')
    filter_horizontal = ('groups', 'rules', )
    inlines = (AliasInline, )

class HostInline(contrib.admin.TabularInline):
    model = Host
    fields = ('hostname', 'ipv4', 'ipv6', 'pub_ipv4', 'mac', 'shared_ip',
        'owner', 'reverse')

class VlanAdmin(admin.ModelAdmin):
    list_display = ('vid', 'name', 'rules_l', 'ipv4', 'net_ipv4', 'ipv6',
        'net_ipv6', 'description', 'domain', 'snat_ip', 'snat_to_l')
    ordering = ('vid', )
    inlines = (HostInline, )

class RuleAdmin(admin.ModelAdmin):
    list_display = ('r_type', 'color_desc', 'description', 'vlan_l',
        'owner', 'extra', 'direction', 'accept', 'proto', 'sport', 'dport',
        'nat', 'nat_dport')
    list_filter = ('r_type', 'vlan', 'owner', 'direction', 'accept',
        'proto', 'nat')

class AliasAdmin(admin.ModelAdmin):
    list_display = ('alias', 'host')

class SettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'value')


admin.site.register(Host, HostAdmin)
admin.site.register(Vlan, VlanAdmin)
admin.site.register(Rule, RuleAdmin)
admin.site.register(Alias, AliasAdmin)
admin.site.register(Setting, SettingAdmin)
admin.site.register(Group)
admin.site.register(Firewall)
