from celery.task import Task, PeriodicTask
from django.core.cache import cache
import os
import time
from firewall.fw import *

LOCK_EXPIRE = 9 # Lock expires in 5 minutes
lock_id = "blabla"

def reload_firewall_lock():
	acquire_lock = lambda: cache.add(lock_id, "true", LOCK_EXPIRE)

	if acquire_lock():
		print "megszereztem"
		ReloadTask.delay()
	else:
		print "nem szereztem meg"


class ReloadTask(Task):
	def run(self, **kwargs):
		print "indul"
		time.sleep(10)

		try:
			print "ipv4"
			ipv4 = firewall()
			ipv4.reload()
#			print ipv4.show()
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
