from django.contrib import admin
from firewall.models import *


class HostAdmin(admin.ModelAdmin):
    list_display = ('hostname', 'vlan', 'ipv4', 'ipv6', 'mac', 'owner', 'groups_l', 'rules_l', 'description')
    ordering = ('-hostname',)

class VlanAdmin(admin.ModelAdmin):
    list_display = ('vid', 'name', 'en_dst_vlan', 'ipv4', 'net_ipv4', 'ipv6', 'net_ipv6', 'description', 'domain')
    ordering = ('-vid',)

class RuleAdmin(admin.ModelAdmin):
    list_display = ('description', 'vlan', 'extra', 'direction', 'action')

admin.site.register(Host, HostAdmin)
admin.site.register(Vlan, VlanAdmin)
admin.site.register(Rule, RuleAdmin)
admin.site.register(Group)
admin.site.register(Firewall)

