# -*- coding: utf-8 -*-
from django_extensions.management.jobs import HourlyJob
import datetime
from django.utils.timezone import utc
from one.models import Instance
from django.template.loader import render_to_string
from one.tasks import SendMailTask
from django.utils.translation import ugettext_lazy as _
from cloud.settings import CLOUD_URL as url
from django.utils import translation

class Job(HourlyJob):
    help = "Suspend/delete expired Instances."

    def calc(self, orig, days=0, hours=0):
        return (orig + datetime.timedelta(days=days, hours=hours)).replace(minute=0, second=0, microsecond=0)

    def execute(self):
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        d = {
            '1m': self.calc(orig=now, days=30),
            '2w': self.calc(orig=now, days=14),
            '1w': self.calc(orig=now, days=7),
            '1d': self.calc(orig=now, days=1),
            '1h': self.calc(orig=now, hours=1),
        }
        # for i in d:
        #    print i+':'+unicode(d[i])

        # delete
        for i in Instance.objects.filter(state__in=['ACTIVE', 'STOPPED'], time_of_delete__isnull=False):
            try:
                translation.activate(i.owner.person_set.get().language)
            except:
                pass
#            print u'%s delete: %s' % (i.name, i.time_of_delete)
            delete = i.time_of_delete.replace(minute=0, second=0, microsecond=0)
            continue
            if i.time_of_delete < now:
                # msg = render_to_string('mails/notification-delete-now.txt', { 'user': i.owner, 'instance': i, 'url': url } )
                # SendMailTask.delay(to=i.owner.email, subject='[IK Cloud] %s' % i.name, msg=msg)
                pass
            else:
                for t in d:
                    if delete == d[t]:
                        msg = render_to_string('mails/notification-delete.txt', { 'user': i.owner, 'instance': i, 'url': url } )
                        SendMailTask.delay(to=i.owner.email, subject='[IK Cloud] %s' % i.name, msg=msg)

        # suspend
        for i in Instance.objects.filter(state='ACTIVE', time_of_suspend__isnull=False):
            try:
                translation.activate(i.owner.person_set.get().language)
            except:
                pass
#            print u'%s suspend: %s' % (i.name, i.time_of_suspend)
            suspend = i.time_of_suspend.replace(minute=0, second=0, microsecond=0)

            if i.time_of_suspend < now:
                msg = render_to_string('mails/notification-suspend-now.txt', { 'user': i.owner, 'instance': i, 'url': url } )
                SendMailTask.delay(to=i.owner.email, subject='[IK Cloud] %s' % i.name, msg=msg)
                i.stop()
            else:
                for t in d:
                    if suspend == d[t]:
                        msg = render_to_string('mails/notification-suspend.txt', { 'user': i.owner, 'instance': i, 'url': url } )
                        SendMailTask.delay(to=i.owner.email, subject='[IK Cloud] %s' % i.name, msg=msg)
