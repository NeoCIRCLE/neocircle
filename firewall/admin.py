from django.contrib import admin
from firewall.models import *


class HostAdmin(admin.ModelAdmin):
    list_display = ('hostname', 'vlan', 'ipv4', 'ipv6', 'mac', 'owner', 'groups_l', 'rules_l', 'description')
    ordering = ('-hostname',)

class VlanAdmin(admin.ModelAdmin):
    list_display = ('vid', 'name', 'rules_l', 'ipv4', 'net_ipv4', 'ipv6', 'net_ipv6', 'description', 'domain', 'snat_ip', 'snat_to_l')
    ordering = ('-vid',)

class RuleAdmin(admin.ModelAdmin):
    list_display = ('r_type', 'desc', 'description', 'vlan_l', 'owner', 'extra', 'direction', 'action', 'nat', 'nat_dport')

admin.site.register(Host, HostAdmin)
admin.site.register(Vlan, VlanAdmin)
admin.site.register(Rule, RuleAdmin)
admin.site.register(Group)
admin.site.register(Firewall)

