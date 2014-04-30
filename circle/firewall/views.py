# Copyright 2014 Budapest University of Technology and Economics (BME IK)
#
# This file is part of CIRCLE Cloud.
#
# CIRCLE is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# CIRCLE is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along
# with CIRCLE.  If not, see <http://www.gnu.org/licenses/>.

import base64
import datetime
import json

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpResponse
from django.utils.timezone import utc
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .tasks.local_tasks import reloadtask
from .models import BlacklistItem, Host


def reload_firewall(request):
    if request.user.is_authenticated():
        if request.user.is_superuser:
            html = (_("Dear %s, you've signed in as administrator!<br />"
                      "Reloading in 10 seconds...") % request.user.username)
            reloadtask.delay()
            reloadtask.delay('Vlan')
        else:
            html = (_("Dear %s, you've signed in!") % request.user.username)
    else:
        html = _("Dear anonymous, you've not signed in yet!")
    return HttpResponse(html)


@csrf_exempt
@require_POST
def firewall_api(request):
    try:
        data = json.loads(base64.b64decode(request.POST["data"]))
        command = request.POST["command"]
        if data["password"] != "bdmegintelrontottaanetet":
            raise Exception(_("Wrong password."))

        if command == "blacklist":
            obj, created = BlacklistItem.objects.get_or_create(ipv4=data["ip"])
            obj.reason = data["reason"]
            obj.snort_message = data["snort_message"]
            if created:
                try:
                    obj.host = Host.objects.get(ipv4=data["ip"])
                except (Host.DoesNotExist, ValidationError,
                        IntegrityError, AttributeError):
                    pass

            modified = obj.modified_at + datetime.timedelta(minutes=1)
            now = datetime.dateime.utcnow().replace(tzinfo=utc)
            if obj.type == 'tempwhite' and modified < now:
                obj.type = 'tempban'
            if obj.type != 'whitelist':
                obj.save()
            return HttpResponse(unicode(_("OK")))
        else:
            raise Exception(_("Unknown command."))

    except (ValidationError, IntegrityError, AttributeError, Exception) as e:
        return HttpResponse(_("Something went wrong!\n%s\n") % e)
    except:
        return HttpResponse(_("Something went wrong!\n"))

    return HttpResponse(unicode(_("OK")))
