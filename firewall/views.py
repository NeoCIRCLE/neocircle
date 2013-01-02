from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.shortcuts import render_to_response
from firewall.models import *
from firewall.fw import *
from django.views.decorators.csrf import csrf_exempt              
from django.db import IntegrityError               
from tasks import *
from celery.task.control import inspect

import re
import base64
import json
import sys


def reload_firewall(request):
	if request.user.is_authenticated():
		if(request.user.is_superuser):
			html = u"Be vagy jelentkezve es admin is vagy, kedves %s!" % request.user.username
			html += "<br> 10 masodperc mulva ujratoltodik"
			ReloadTask.delay()
		else:
			html = u"Be vagy jelentkezve, csak nem vagy admin, kedves %s!" % request.user.username
	else:
		html = u"Nem vagy bejelentkezve, kedves ismeretlen!"
	return HttpResponse(html)

@csrf_exempt
def firewall_api(request):
	if request.method == 'POST':
		try:
			data=json.loads(base64.b64decode(request.POST["data"]))
			command = request.POST["command"]
			if(data["password"] != "bdmegintelrontottaanetet"):
				raise Exception("rossz jelszo")

			data["hostname"] = re.sub(r' ','_', data["hostname"])

			if(command == "create"):
				data["owner"] = "opennebula"
				owner = auth.models.User.objects.get(username=data["owner"])
				host = models.Host(hostname=data["hostname"], vlan=models.Vlan.objects.get(name=data["vlan"]), mac=data["mac"], ipv4=data["ip"], owner=owner, description=data["description"], pub_ipv4=models.Vlan.objects.get(name=data["vlan"]).snat_ip, shared_ip=True)
				host.full_clean()
				host.save()

				host.enable_net()

				for p in data["portforward"]:
					host.add_port(proto=p["proto"], public=int(p["public_port"]), private=int(p["private_port"]))

			elif(command == "destroy"):
				data["owner"] = "opennebula"
				print data["hostname"]
				owner = auth.models.User.objects.get(username=data["owner"])
				host = models.Host.objects.get(hostname=data["hostname"], owner=owner)

				host.del_rules()
				host.delete()
			else:
				raise Exception("rossz parancs")

			reload_firewall_lock()
		except (ValidationError, IntegrityError, AttributeError, Exception) as e:
			return HttpResponse(u"rosszul hasznalod! :(\n%s\n" % e);
		except:
#			raise
			return HttpResponse(u"rosszul hasznalod! :(\n");
		
		return HttpResponse(u"ok");

	return HttpResponse(u"ez kerlek egy api lesz!\n");


