from datetime import datetime
import logging
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from manager.mancelery import celery
from vm.models import Node, Instance

logger = logging.getLogger(__name__)


@celery.task(ignore_result=True)
def update_domain_states():
    nodes = Node.objects.filter(enabled=True).all()
    for node in nodes:
        node.update_vm_states()


@celery.task(ignore_result=True)
def garbage_collector(timeout=15):
    """Garbage collector for instances.

    Suspends and destroys expired instances.

    :param timeout: Seconds before TimeOut exception
    :type timeout: int
    """
    now = timezone.now()
    for i in Instance.objects.filter(destroyed=None).all():
        if i.time_of_delete and now < i.time_of_delete:
            i.destroy_async()
            logger.info("Expired instance %d destroyed.", i.pk)
            try:
                i.owner.profile.notify(
                    _('Machine destroyed'),
                    'dashboard/notifications/vm-destroyed.html',
                    {'instance': i})
            except:
                logger.debug('Could not notify owner of instance %d.', i.pk)
        elif (i.time_of_suspend and now < i.time_of_suspend and
              i.state == 'RUNNING'):
            i.sleep_async()
            logger.info("Expired instance %d suspended." % i.pk)
            try:
                i.owner.profile.notify(
                    _('Machine suspended'),
                    'dashboard/notifications/vm-suspended.html',
                    {'instance': i})
            except:
                logger.debug('Could not notify owner of instance %d.', i.pk)
        else:
            logger.debug("Instance %d didn't expire." % i.pk)
