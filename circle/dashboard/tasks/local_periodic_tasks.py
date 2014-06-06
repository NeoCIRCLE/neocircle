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

import logging
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import ungettext, override

from manager.mancelery import celery
from ..models import Notification

logger = logging.getLogger(__name__)


@celery.task(ignore_result=True)
def send_email_notifications():
    msgs = {}
    for i in Notification.objects.filter(status=Notification.STATUS.new,
                                         valid_until__lt=timezone.now()):
        if i.to not in msgs:
            msgs[i.to] = []
        msgs[i.to].append(i)

    from_email = settings['DEFAULT_FROM_EMAIL']

    for user, i in msgs.iteritems:
        if (not user.profile or not user.email or not
                user.profile.email_notifications):
            continue
        with override(user.profile.language):
            context = {'user': user, 'messages': i}
            subject = ungettext("%d new notification",
                                "%d new notifications", len(i)) % len(i)
            body = render_to_string('dashboard/notifications/email.txt',
                                    context)
        try:
            send_mail(subject, body, from_email, (user.email, ))
        except:
            logger.error("Failed to send mail to", user, exc_info=True)
        else:
            for j in i:
                j.status = j.STATUS.delivered
                j.save()
