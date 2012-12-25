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
			try:
				print "ipv4"
				ipv4 = firewall()
#				html += ipv4.show()
				ipv4.reload()
				print "ipv6"
				ipv6 = firewall(True)
				ipv6.reload()
				print "dns"
				dns()
				print "dhcp"
				dhcp()
				print "vege"
				html += "<br>sikerult :)"
			except:
				raise
				html += "<br>nem sikerult :("
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
				host = models.Host(hostname=data["hostname"], vlan=models.Vlan.objects.get(name=data["vlan"]), mac=data["mac"], ipv4=data["ip"], owner=owner, description=data["description"])
				host.full_clean()
				host.save()

				rule = models.Rule(direction=False, owner=owner, description="%s netezhet" % (data["hostname"]), accept=True, r_type="host", nat_dport=0)
				rule.save()
				rule.vlan.add(models.Vlan.objects.get(name="PUB"))
				host.rules.add(rule)

				for p in data["portforward"]:
					proto = "tcp" if (p["proto"] == "tcp") else "udp"
					rule = models.Rule(direction=True, owner=owner, description="%s %s %s->%s" % (data["hostname"], proto, p["public_port"], p["private_port"]), dport=int(p["public_port"]), proto=p["proto"], nat=True, accept=True, r_type="host", nat_dport=int(p["private_port"]))
					rule.save()
					rule.vlan.add(models.Vlan.objects.get(name="PUB"))
					rule.vlan.add(models.Vlan.objects.get(name="DMZ"))
					rule.vlan.add(models.Vlan.objects.get(name="VM-NET"))
					rule.vlan.add(models.Vlan.objects.get(name="WAR"))
					host.rules.add(rule)

			elif(command == "destroy"):
				data["owner"] = "opennebula"
				print data["hostname"]
				owner = auth.models.User.objects.get(username=data["owner"])
				host = models.Host.objects.get(hostname=data["hostname"], owner=owner)

				for rule in host.rules.filter(owner=owner):
					rule.delete()

				host.delete()
			else:
				raise Exception("rossz parancs")

			lock("asd")
		except (ValidationError, IntegrityError, AttributeError, Exception) as e:
			return HttpResponse(u"rosszul hasznalod! :(\n%s\n" % e);
		except:
#			raise
			return HttpResponse(u"rosszul hasznalod! :(\n");
		
		return HttpResponse(u"ok");

	return HttpResponse(u"ez kerlek egy api lesz!\n");


