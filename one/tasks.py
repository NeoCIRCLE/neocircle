from celery.task import Task, PeriodicTask
import logging
import celery
import os
import sys
import time
from django.core.mail import send_mail
from one.models import Instance

logger = logging.getLogger(__name__)

class SendMailTask(Task):
    def run(self, to, subject, msg, sender=u'noreply@cloud.ik.bme.hu'):
        send_mail(subject, msg, sender, [ to ], fail_silently=False)
        logger.info("[django][one][tasks.py] %s->%s [%s]" % (sender, to, subject) )


class UpdateInstanceStateTask(Task):
    def run(self, one_id):
        print one_id
        try:
            inst = Instance.objects.get(one_id=one_id)
        except:
            print 'nincs ilyen'
            return
        inst.update_state()
        inst.waiting = False
        inst.save()
        print inst.state
