from celery.task import Task, PeriodicTask
import celery
from django.core.cache import cache
import os
import time
from firewall.fw import *
from django.conf.settings import firewall_settings as settings

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
            print "dhcp ujratoltese kesz"

        if cache.get('firewall_lock'):
            cache.delete("firewall_lock")
            ipv4 = Firewall().get()
            ipv6 = Firewall(True).get()
            reload_firewall_task.delay(ipv4, ipv6)
            print "firewall ujratoltese kesz"

        if cache.get('blacklist_lock'):
            cache.delete("blacklist_lock")
            reload_blacklist_task.delay(list(ipset()))
            print "blacklist ujratoltese kesz"

class ReloadTask(Task):
    def run(self, type='Host'):

        if type in ["Host", "Records", "Domain", "Vlan"]:
            cache.add("dns_lock", "true", 30)

        if type == "Host":
            cache.add("dhcp_lock", "true", 30)

        if type in ["Host", "Rule", "Firewall"]:
            cache.add("firewall_lock", "true", 30)

        if type == "Blacklist":
            cache.add("blacklist_lock", "true", 30)

        print type

