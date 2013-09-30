from manager.mancelery import celery
from django.core.cache import cache
from firewall.fw import Firewall, dhcp, dns, ipset
import django.conf
import remote_tasks
settings = django.conf.settings.FIREWALL_SETTINGS


@celery.task
def periodic_task():
        if cache.get('dns_lock'):
            cache.delete("dns_lock")
            remote_tasks.reload_dns_task.apply_async(args=[dns()],
                                                     queue='firewall')
            print "dns ujratoltese kesz"

        if cache.get('dhcp_lock'):
            cache.delete("dhcp_lock")
            remote_tasks.reload_dhcp_task.delay(dhcp())
            print "dhcp ujratoltese kesz"

        if cache.get('firewall_lock'):
            cache.delete("firewall_lock")
            ipv4 = Firewall().get()
            ipv6 = Firewall(True).get()
            remote_tasks.reload_firewall_task.delay(ipv4, ipv6)
            print "firewall ujratoltese kesz"

        if cache.get('blacklist_lock'):
            cache.delete("blacklist_lock")
            remote_tasks.reload_blacklist_task.delay(list(ipset()))
            print "blacklist ujratoltese kesz"


@celery.task
def reloadtask(type='Host'):
        if type in ["Host", "Record", "Domain", "Vlan"]:
            cache.add("dns_lock", "true", 30)

        if type == "Host":
            cache.add("dhcp_lock", "true", 30)

        if type in ["Host", "Rule", "Firewall"]:
            cache.add("firewall_lock", "true", 30)

        if type == "Blacklist":
            cache.add("blacklist_lock", "true", 30)

        print type
