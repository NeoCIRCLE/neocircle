from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.shortcuts import render_to_response
from firewall.models import *
from firewall.fw import *

def reload_firewall(request):
	if request.user.is_authenticated():
		if(request.user.is_superuser):
			html = u"Be vagy jelentkezve es admin is vagy, kedves %s!" % request.user.username
			try:
				print "ipv4"
				ipv4 = firewall()
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
				html += "<br>nem sikerult :("
		else:
			html = u"Be vagy jelentkezve, csak nem vagy admin, kedves %s!" % request.user.username
	else:
		html = u"Nem vagy bejelentkezve, kedves ismeretlen!"
	return HttpResponse(html)
