from django.contrib import admin
from firewall.models import *


class HostAdmin(admin.ModelAdmin):
    list_display = ('hostname', 'vlan', 'ipv4', 'ipv6', 'pub_ipv4', 'mac', 'shared_ip', 'owner', 'groups_l', 'rules_l', 'description')
    ordering = ('hostname',)
    list_filter = ('owner', 'vlan', 'groups')
    search_fields = ('hostname', 'description', 'ipv4', 'ipv6', 'mac')
    filter_horizontal = ('groups', 'rules',)

class VlanAdmin(admin.ModelAdmin):
    list_display = ('vid', 'name', 'rules_l', 'ipv4', 'net_ipv4', 'ipv6', 'net_ipv6', 'description', 'domain', 'snat_ip', 'snat_to_l')
    ordering = ('vid',)

class RuleAdmin(admin.ModelAdmin):
    list_display = ('r_type', 'desc', 'description', 'vlan_l', 'owner', 'extra', 'direction', 'accept', 'proto', 'sport', 'dport', 'nat', 'nat_dport')
    list_filter = ('r_type', 'vlan', 'owner', 'direction', 'accept', 'proto', 'nat')

admin.site.register(Host, HostAdmin)
admin.site.register(Vlan, VlanAdmin)
admin.site.register(Rule, RuleAdmin)
admin.site.register(Group)
admin.site.register(Firewall)

