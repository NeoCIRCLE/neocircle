from celery.task import Task
import logging
from django.core.mail import send_mail
from django.conf import settings
from one.models import Instance

logger = logging.getLogger(__name__)


class SendMailTask(Task):
    def run(self, to, subject, msg, sender=None):
        if sender is None:
            if settings.SITE_NAME:
                sender = '"%s" <%s>' % (settings.SITE_NAME.replace('"', ''),
                                        settings.DEFAULT_FROM_EMAIL)
            else:
                sender = settings.DEFAULT_FROM_EMAIL
        send_mail(subject, msg, sender, [to, ], fail_silently=False)
        logger.info("[django][one][tasks] %s->%s %s" % (sender, to, subject))


class UpdateInstanceStateTask(Task):
    def run(self, one_id, new_state):
        print one_id
        try:
            inst = Instance.objects.get(one_id=one_id)
        except:
            print 'nincs ilyen'
            return
        inst.state = new_state
        inst.waiting = False
        inst.save()
        if inst.template.state == 'SAVING':
            inst.check_if_is_save_as_done()
        print inst.state

# ezek csak azert vannak felveve, hogy szepen meg lehessen hivni oket
# ezeket a fejgepen futo celery futtatja


class CreateInstanceTask(Task):
    def run(self, name, instance_type, disk_id, network_id, ctx):
        pass


class DeleteInstanceTask(Task):
    def run(self, one_id):
        pass


class ChangeInstanceStateTask(Task):
    def run(self, one_id, new_state):
        pass


class SaveAsTask(Task):
    def run(self, one_id, new_img):
        pass


class UpdateDiskTask(Task):
    def run(self):
        pass


class UpdateNetworkTask(Task):
    def run(self):
        pass

class GetInstanceStateTask(Task):
    def run(self, one_id):
        pass
