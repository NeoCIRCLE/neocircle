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

from __future__ import absolute_import, unicode_literals

from datetime import timedelta
from json import dumps
import logging

from netaddr import AddrFormatError, IPAddress
from requests import post
from requests.exceptions import RequestException

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import BlacklistItem, Host

from django.conf import settings

logger = logging.getLogger(__name__)


def send_request(obj):
    data = {"ip": obj.ipv4,
            "msg": obj.snort_message,
            "reason": obj.reason,
            "expires_at": str(obj.expires_at).split('.')[0],
            "object_kind": "ban"}
    if obj.host:
        data.update({"hostname": obj.host.hostname,
                     "username": obj.host.owner.username,
                     "fullname": obj.host.owner.get_full_name()})
    try:
        r = post(settings.BLACKLIST_HOOK_URL, data=dumps(data, indent=2),
                 timeout=3)
        r.raise_for_status()
    except RequestException as e:
        logger.warning("Error in HTTP POST: %s. url: %s params: %s",
                       str(e), settings.BLACKLIST_HOOK_URL, data)
    else:
        logger.info("Successful HTTP POST. url: %s params: %s",
                    settings.BLACKLIST_HOOK_URL, data)


@csrf_exempt
@require_POST
def add_blacklist_item(request):
    password = request.POST.get('password')
    if (not settings.BLACKLIST_PASSWORD or
            password != settings.BLACKLIST_PASSWORD):
        logger.warning("Tried invalid password. Password: %s IP: %s",
                       password, request.META["REMOTE_ADDR"])
        raise PermissionDenied()

    try:
        address = request.POST.get('address')
        address_object = IPAddress(address, version=4)
    except (AddrFormatError, TypeError) as e:
        logger.warning("Invalid IP address: %s (%s)", address, str(e))
        return HttpResponse(_("Invalid IP address."))

    obj, created = BlacklistItem.objects.get_or_create(ipv4=address)
    if created:
        try:
            db_format = '.'.join("%03d" % x for x in address_object.words)
            obj.host = Host.objects.get(ipv4=db_format)
        except Host.DoesNotExist:
            pass

    now = timezone.now()
    can_update = (
        (obj.whitelisted and obj.expires_at and now > obj.expires_at) or
        not obj.whitelisted)
    is_new = created or (obj.expires_at and now > obj.expires_at)

    if created or can_update:
        obj.reason = request.POST.get('reason')
        obj.snort_message = request.POST.get('snort_message')
        obj.whitelisted = False
        obj.expires_at = now + timedelta(weeks=1)
        obj.full_clean()
        obj.save()

    if created:
        logger.info("Successfully created blacklist item %s.", address)
    elif can_update:
        logger.info("Successfully modified blacklist item %s.", address)

    if is_new and settings.BLACKLIST_HOOK_URL:
        send_request(obj)

    return HttpResponse(unicode(_("OK")))
