from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.shortcuts import render_to_response
from firewall.models import *
from firewall.fw import *
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db import IntegrityError
from tasks import *
from celery.task.control import inspect
from django.utils.translation import ugettext_lazy as _

import re
import base64
import json
import sys


def reload_firewall(request):
    if request.user.is_authenticated():
        if request.user.is_superuser:
            html = ((_("Dear %s, you've signed in as administrator!") %
                    request.user.username) + "<br />" +
                    _("Reloading in 10 seconds..."))
            ReloadTask.delay()
        else:
            html = (_("Dear %s, you've signed in!")
                    % request.user.username)
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
            if created:
                obj.reason=data["reason"]
                obj.snort_message=data["snort_message"]
            obj.save()
            return HttpResponse(_("OK"));

        if not (data["vlan"] == "vm-net" or data["vlan"] == "war"):
            raise Exception(_("Only vm-net and war can be used."))

        data["hostname"] = re.sub(r' ','_', data["hostname"])

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

            host.del_rules()
            host.delete()
        else:
            raise Exception(_("Unknown command."))

    except (ValidationError, IntegrityError, AttributeError, Exception) as e:
        return HttpResponse(_("Something went wrong!\n%s\n") % e);
    except:
        return HttpResponse(_("Something went wrong!\n"));
 
    return HttpResponse(_("OK"));
