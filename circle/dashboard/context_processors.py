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

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from .models import Message


def notifications(request):
    count = (request.user.notification_set.filter(status="new").count()
             if request.user.is_authenticated() else None)
    return {
        'NEW_NOTIFICATIONS_COUNT': count
    }


def extract_settings(request):
    return {
        'COMPANY_NAME': getattr(settings, "COMPANY_NAME", None),
        'ADMIN_ENABLED': getattr(settings, "ADMIN_ENABLED", False),
    }


def broadcast_messages(request):
    now = timezone.now()
    messages = Message.objects.filter(enabled=True).exclude(
        Q(starts_at__gt=now) | Q(ends_at__lt=now))
    return {'broadcast_messages': messages}
