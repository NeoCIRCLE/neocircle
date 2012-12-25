from celery.task import Task, PeriodicTask
from django.core.cache import cache
import os
from firewall.fw import *

LOCK_EXPIRE = 9 # Lock expires in 5 minutes
lock_id = "blabla"

def lock(para):

	acquire_lock = lambda: cache.add(lock_id, "true", LOCK_EXPIRE)

	if acquire_lock():
		print "megszereztem"
		ReloadTask.delay("asd")
	else:
		print "nem szereztem meg"


class ReloadTask(Task):
	def run(self, para, **kwargs):
		print "indul"
		os.system("sleep 10")

		try:
			print "ipv4"
			ipv4 = firewall()
#			html += ipv4.show()
			ipv4.reload()
			print "ipv6"
			ipv6 = firewall(True)
			ipv6.reload()
			print "dns"
			dns()
			print "dhcp"
			dhcp()
			print "vege"
		except:
			print "nem sikerult :("

		print "leall"
