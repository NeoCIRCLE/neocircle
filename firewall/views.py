from django.shortcuts import render_to_response
from django.http import HttpResponse
from firewall.models import *
from firewall.fw import *
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db import IntegrityError
from tasks import *
from celery.task.control import inspect
from django.utils.translation import ugettext_lazy as _
from django.template.loader import render_to_string

import re
import base64
import json
import sys

import datetime
from django.utils.timezone import utc

def reload_firewall(request):
    if request.user.is_authenticated():
        if request.user.is_superuser:
            html = (_("Dear %s, you've signed in as administrator!<br />"
                      "Reloading in 10 seconds...") % request.user.username)
            ReloadTask.delay()
        else:
            html = (_("Dear %s, you've signed in!") % request.user.username)
    else:
        html = _("Dear anonymous, you've not signed in yet!")
    return HttpResponse(html)

@csrf_exempt
@require_POST
def firewall_api(request):
    try:
        data=json.loads(base64.b64decode(request.POST["data"]))
        command = request.POST["command"]
        if data["password"] != "bdmegintelrontottaanetet":
            raise Exception(_("Wrong password."))

        if command == "blacklist":
            obj, created = Blacklist.objects.get_or_create(ipv4=data["ip"])
            obj.reason=data["reason"]
            obj.snort_message=data["snort_message"]
            if created:
                try:
                    obj.host = models.Host.objects.get(ipv4=data["ip"])
                    user = obj.host.owner
                    lang = user.person_set.all()[0].language
                    s = render_to_string('mails/notification-ban-now.txt', { 'user': user, 'bl': obj } )
                    print s
#                    send_mail(settings.EMAIL_SUBJECT_PREFIX + (_('New project: %s') % p.identifier), s, settings.SERVER_EMAIL, [])
                except (Host.DoesNotExist, ValidationError, IntegrityError, AttributeError):
                    pass
            print obj.modified_at + datetime.timedelta(minutes=5)
            print datetime.datetime.utcnow().replace(tzinfo=utc)
            if obj.type == 'tempwhite' and obj.modified_at + datetime.timedelta(minutes=1) < datetime.datetime.utcnow().replace(tzinfo=utc):
                obj.type = 'tempban'
            obj.save()
            return HttpResponse(unicode(_("OK")))

        if not (data["vlan"] == "vm-net" or data["vlan"] == "war"):
            raise Exception(_("Only vm-net and war can be used."))

        data["hostname"] = re.sub(r' ', '_', data["hostname"])

        if command == "create":
            data["owner"] = "opennebula"
            owner = auth.models.User.objects.get(username=data["owner"])
            host = models.Host(hostname=data["hostname"],
                    vlan=models.Vlan.objects.get(name=data["vlan"]),
                    mac=data["mac"], ipv4=data["ip"], owner=owner,
                    description=data["description"], pub_ipv4=models.
                        Vlan.objects.get(name=data["vlan"]).snat_ip,
                    shared_ip=True)
            host.full_clean()
            host.save()

            host.enable_net()

            for p in data["portforward"]:
                host.add_port(proto=p["proto"],
                        public=int(p["public_port"]),
                        private=int(p["private_port"]))

        elif command == "destroy":
            data["owner"] = "opennebula"
            print data["hostname"]
            owner = auth.models.User.objects.get(username=data["owner"])
            host = models.Host.objects.get(hostname=data["hostname"],
                    owner=owner)

            host.delete()
        else:
            raise Exception(_("Unknown command."))

    except (ValidationError, IntegrityError, AttributeError, Exception) as e:
        return HttpResponse(_("Something went wrong!\n%s\n") % e)
    except:
        return HttpResponse(_("Something went wrong!\n"))

    return HttpResponse(unicode(_("OK")))
