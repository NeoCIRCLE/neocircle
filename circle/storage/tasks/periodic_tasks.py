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

from storage.models import DataStore
from manager.mancelery import celery
import logging
from storage.tasks import storage_tasks

logger = logging.getLogger(__name__)


@celery.task
def garbage_collector(timeout=15, percent=10):
    """ Garbage collector for disk images.

    If there is not enough free space on datastore (default 10%)
    deletes oldest images from trash.

    :param timeout: Seconds before TimeOut exception
    :type timeout: int
    """
    for ds in DataStore.objects.all():
        queue_name = ds.get_remote_queue_name('storage', priority='fast')
        files = set(storage_tasks.list_files.apply_async(
            args=[ds.type, ds.path], queue=queue_name).get(timeout=timeout))
        disks = ds.get_deletable_disks()
        queue_name = ds.get_remote_queue_name('storage', priority='slow')

        deletable_disks = [disk for disk in disks if disk in files]
        for i in deletable_disks:
            logger.info("Image: %s at Datastore: %s fetch for destroy." %
                        (i, ds.path))
        try:
            success = storage_tasks.make_free_space.apply_async(
                args=[ds.type, ds.path, deletable_disks, percent],
                queue=queue_name).get(timeout=timeout)
            if not success:
                logger.warning("Has no deletable disk.")
        except Exception as e:
            logger.warning(str(e))


@celery.task
def list_orphan_disks(timeout=15):
    """List disk image files without Disk object in the database.

    Exclude cloud-xxxxxxxx.dump format images.

    :param timeout: Seconds before TimeOut exception
    :type timeout: int
    """
    import re
    for ds in DataStore.objects.all():
        for i in ds.get_orphan_disks(timeout=timeout):
            if not re.match('cloud-[0-9]*\.dump', i):
                logging.warning("Orphan disk: %s" % i)


@celery.task
def list_missing_disks(timeout=15):
    """List Disk objects without disk image files.

    :param timeout: Seconds before TimeOut exception
    :type timeout: int
    """
    for ds in DataStore.objects.all():
        for i in ds.get_missing_disks(timeout=timeout):
            logging.critical("Image: %s is missing from %s datastore."
                             % (i, ds.path))
