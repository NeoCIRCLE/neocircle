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
import logging

from netaddr import AddrFormatError, IPAddress

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import BlacklistItem, Host

from django.conf import settings

logger = logging.getLogger(__name__)


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
        IPAddress(address, version=4)
    except (AddrFormatError, TypeError) as e:
        logger.warning("Invalid IP address: %s (%s)", address, str(e))
        return HttpResponse(_("Invalid IP address."))

    obj, created = BlacklistItem.objects.get_or_create(ipv4=address)
    if created:
        try:
            obj.host = Host.objects.get(ipv4=address)
        except Host.DoesNotExist:
            pass

    now = timezone.now()
    can_update = ((obj.whitelisted and now > obj.expires_at) or
                  not obj.whitelisted)

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

    return HttpResponse(unicode(_("OK")))
