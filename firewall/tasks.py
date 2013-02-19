from celery.task import Task, PeriodicTask
import celery
from django.core.cache import cache
import os
import time
from firewall.fw import *
from cloud.settings import firewall_settings as settings

@celery.task
def reload_dns_task(data):
    pass
@celery.task
def reload_firewall_task(data4, data6):
    pass
@celery.task
def reload_dhcp_task(data):
    pass

class ReloadTask(Task):
    def run(self, type='Host'):

        sleep=False

        if type in ["Host", "Records", "Domain", "Vlan"]:
            lock = lambda: cache.add("dns_lock", "true", 9)
            if lock():
                if not sleep:
                    sleep = True
                    time.sleep(10)
                reload_dns_task.delay(dns())

        if type == "Host":
            lock = lambda: cache.add("dhcp_lock", "true", 9)
            if lock():
                if not sleep:
                    sleep = True
                    time.sleep(10)
                reload_dhcp_task.delay(dhcp())

        if type in ["Host", "Rule", "Firewall"]:
            lock = lambda: cache.add("firewall_lock", "true", 9)
            if lock():
                if not sleep:
                    sleep = True
                    time.sleep(10)
                ipv4 = firewall().get()
                ipv6 = firewall(True).get()
                reload_firewall_task.delay(ipv4, ipv6)

        print type

