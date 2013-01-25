from celery.task import Task, PeriodicTask
from django.core.cache import cache
import os
import time
from firewall.fw import *
from firewall.models import settings

def reload_firewall_lock():
    acquire_lock = lambda: cache.add("reload_lock1", "true", 9)

    if acquire_lock():
        print "megszereztem"
        ReloadTask.delay()
    else:
        print "nem szereztem meg"


class ReloadTask(Task):
    def run(self, **kwargs):
        acquire_lock = lambda: cache.add("reload_lock1", "true", 90)
        release_lock = lambda: cache.delete("reload_lock1")

        if not acquire_lock():
            print "mar folyamatban van egy reload"
            return

        print "indul"
        try:
            sleep = float(settings['reload_sleep'])
        except:
            sleep = 10
        time.sleep(sleep)

        try:
            print "ipv4"
            ipv4 = firewall()
            ipv4.reload()
#           print ipv4.show()
            print "ipv6"
            ipv6 = firewall(True)
            ipv6.reload()
            print "dns"
            dns()
            print "dhcp"
            dhcp()
            print "vege"
        except:
            raise
            print "nem sikerult :("

        print "leall"
        release_lock()
