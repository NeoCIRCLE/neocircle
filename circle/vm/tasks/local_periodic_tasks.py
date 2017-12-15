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
from django.utils import timezone
from django.utils.translation import ugettext_noop

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
    for i in Instance.objects.filter(destroyed_at=None).all():
        if i.time_of_delete and now > i.time_of_delete:
            i.destroy.async(system=True)
            logger.info("Expired instance %d destroyed.", i.pk)
            try:
                i.owner.profile.notify(
                    ugettext_noop('%(instance)s destroyed'),
                    ugettext_noop(
                        'Your instance <a href="%(url)s">%(instance)s</a> '
                        'has been destroyed due to expiration.'),
                    instance=i.name, url=i.get_absolute_url())
            except Exception as e:
                logger.debug('Could not notify owner of instance %d .%s',
                             i.pk, unicode(e))
        elif (i.time_of_suspend and now > i.time_of_suspend and
              i.state == 'RUNNING'):
            i.sleep.async(system=True)
            logger.info("Expired instance %d suspended." % i.pk)
            try:
                i.owner.profile.notify(
                    ugettext_noop('%(instance)s suspended'),
                    ugettext_noop(
                        'Your instance <a href="%(url)s">%(instance)s</a> '
                        'has been suspended due to expiration. '
                        'You can resume or destroy it.'),
                    instance=i.name, url=i.get_absolute_url())
            except Exception as e:
                logger.debug('Could not notify owner of instance %d .%s',
                             i.pk, unicode(e))
        elif i.is_expiring():
            logger.debug("Instance %d expires soon." % i.pk)
            i.notify_owners_about_expiration()
        else:
            logger.debug("Instance %d didn't expire." % i.pk)


@celery.task(ignore_result=True)
def auto_migrate():  # Dummy implementation
    import time
    logger.info("Auto migration has started.")
    time.sleep(10)
    logger.info("Auto migration has finished.")
