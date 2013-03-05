from celery.task import Task, PeriodicTask
import logging
import celery
import os
import sys
import time


logger = logging.getLogger(__name__)

class SendMailTask(Task):
    def run(self, to, subject, msg):
        sender = u'cloud@ik.bme.hu'
        print u'%s->%s [%s]' % (sender, to, subject)
        logger.info("[django][one][tasks.py] %s", msg)
