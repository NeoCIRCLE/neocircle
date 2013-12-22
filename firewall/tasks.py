from celery.task import Task, PeriodicTask
import celery
from django.core.cache import cache
import os
import time
from firewall.fw import *
import django.conf

settings = django.conf.settings.FIREWALL_SETTINGS

@celery.task
def reload_dns_task(data):
    pass
@celery.task
def reload_firewall_task(data4, data6):
    pass
@celery.task
def reload_dhcp_task(data):
    pass
@celery.task
def reload_blacklist_task(data):
    pass

# new tasks

@celery.task(name='firewall.reload_firewall')
def reload_firewall(data4, data6):
    pass


@celery.task(name='firewall.reload_firewall_vlan')
def reload_firewall_vlan(data):
    pass


@celery.task(name='firewall.reload_dhcp')
def reload_dhcp(data):
    pass


@celery.task(name='firewall.reload_blacklist')
def reload_blacklist(data):
    pass


class Periodic(PeriodicTask):
    run_every = timedelta(seconds=10)

    def run(self, **kwargs):

        if cache.get('dns_lock'):
            cache.delete("dns_lock")
            reload_dns_task.delay(dns())
            print "dns ujratoltese kesz"

        if cache.get('dhcp_lock'):
            cache.delete("dhcp_lock")
            reload_dhcp_task.delay(dhcp())
            reload_dhcp.apply_async(args=[dhcp()], queue='dhcp2')
            print "dhcp ujratoltese kesz"

        if cache.get('firewall_lock'):
            cache.delete("firewall_lock")
            ipv4 = Firewall().get()
            ipv6 = Firewall(True).get()
            # old
            reload_firewall_task.apply_async((ipv4, ipv6), queue='firewall')
            # new
            reload_firewall.apply_async(args=[ipv4, ipv6], queue='firewall2')
            print "firewall ujratoltese kesz"

        if cache.get('firewall_vlan_lock'):
             cache.delete("firewall_vlan_lock")
             data = vlan()
#             reload_firewall_vlan.apply_async(args=[data], queue='firewall')
             reload_firewall_vlan.apply_async(args=[data], queue='firewall2')
             print "firewall_vlan ujratoltese kesz"


        if cache.get('blacklist_lock'):
            cache.delete("blacklist_lock")
            # old
            reload_blacklist_task.delay(list(ipset()))
            # new
            reload_blacklist.apply_async(args=[list(ipset())], queue='firewall2')
            print "blacklist ujratoltese kesz"

class ReloadTask(Task):
    def run(self, type='Host'):

        if type in ["Host", "Records", "Domain", "Vlan"]:
            cache.add("dns_lock", "true", 30)

        if type in ["Host", "Vlan"]:
            cache.add("dhcp_lock", "true", 30)

        if type in ["Host", "Rule", "Firewall", "Vlan"]:
            cache.add("firewall_lock", "true", 30)

        if type == "Blacklist":
            cache.add("blacklist_lock", "true", 30)

        if type in ["Vlan"]:
             cache.add("firewall_vlan_lock", "true", 30)

        print type

