from manager.mancelery import celery
from django.core.cache import cache
import django.conf
settings = django.conf.settings.FIREWALL_SETTINGS


@celery.task
def periodic_task():
        from firewall.fw import Firewall, dhcp, dns, ipset, vlan
        import remote_tasks

        if cache.get('dns_lock'):
            cache.delete("dns_lock")
            remote_tasks.reload_dns.apply_async(args=[dns()],
                                                queue='dns')
            print "dns ujratoltese kesz"

        if cache.get('dhcp_lock'):
            cache.delete("dhcp_lock")
            remote_tasks.reload_dhcp.apply_async(args=[dhcp()],
                                                 queue='firewall')
            print "dhcp ujratoltese kesz"

        if cache.get('firewall_lock'):
            cache.delete("firewall_lock")
            ipv4 = Firewall(proto=4).get()
            ipv6 = Firewall(proto=6).get()
            remote_tasks.reload_firewall.apply_async(args=[ipv4, ipv6],
                                                     queue='firewall')
            print "firewall ujratoltese kesz"

        if cache.get('firewall_vlan_lock'):
            cache.delete("firewall_vlan_lock")
            remote_tasks.reload_firewall_vlan.apply_async(args=[vlan()],
                                                          queue='firewall')
            print "firewall_vlan ujratoltese kesz"

        if cache.get('blacklist_lock'):
            cache.delete("blacklist_lock")
            remote_tasks.reload_blacklist.apply_async(args=[list(ipset())],
                                                      queue='firewall')
            print "blacklist ujratoltese kesz"


@celery.task
def reloadtask(type='Host'):
        if type in ["Host", "Record", "Domain", "Vlan"]:
            cache.add("dns_lock", "true", 30)

        if type in ["Host", "Vlan"]:
            cache.add("dhcp_lock", "true", 30)

        if type in ["Host", "Rule", "Firewall", "Vlan"]:
            cache.add("firewall_lock", "true", 30)

        if type == "Blacklist":
            cache.add("blacklist_lock", "true", 30)

        if type in ["Vlan", "SwitchPort", "EthernetDevice"]:
            cache.add("firewall_vlan_lock", "true", 30)

        print type
