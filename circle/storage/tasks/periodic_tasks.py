from storage.models import DataStore
import os
from manager.mancelery import celery
import logging
from storage.tasks import remote_tasks

logger = logging.getLogger(__name__)


@celery.task
def garbage_collector(timeout=15):
    """ Garbage collector for disk images.

    Moves 1 day old deleted images to trash folder.
    If there is not enough free space on datastore (default 10%)
    deletes oldest images from trash.

    :param timeout: Seconds before TimeOut exception
    :type timeoit: int
    """
    for ds in DataStore.objects.all():
        file_list = os.listdir(ds.path)
        disk_list = ds.get_deletable_disks()
        queue_name = ds.get_remote_queue_name('storage')
        for i in set(file_list).intersection(disk_list):
            logger.info("Image: %s at Datastore: %s moved to trash folder." %
                        (i, ds.path))
            remote_tasks.move_to_trash.apply_async(
                args=[ds.path, i], queue=queue_name).get(timeout=timeout)
        try:
            remote_tasks.make_free_space.apply_async(
                args=[ds.path], queue=queue_name).get(timeout=timeout)
        except Exception as e:
            logger.warning(str(e))


@celery.task
def list_orphan_disks(timeout=15):
    """List disk image files without Disk object in the database.

    Exclude cloud-xxxxxxxx.dump format images.

    :param timeout: Seconds before TimeOut exception
    :type timeoit: int
    """
    import re
    for ds in DataStore.objects.all():
        queue_name = ds.get_remote_queue_name('storage')
        files = set(remote_tasks.list_files.apply_async(
            args=[ds.path], queue=queue_name).get(timeout=timeout))
        disks = set([disk.filename for disk in ds.disk_set.all()])
        for i in files - disks:
            if not re.match('cloud-[0-9]*\.dump', i):
                logging.warning("Orphan disk: %s" % i)


@celery.task
def list_missing_disks(timeout=15):
    """List Disk objects without disk image files.

    :param timeout: Seconds before TimeOut exception
    :type timeoit: int
    """
    for ds in DataStore.objects.all():
        queue_name = ds.get_remote_queue_name('storage')
        files = set(remote_tasks.list_files.apply_async(
            args=[ds.path], queue=queue_name).get(timeout=timeout))
        disks = set([disk.filename for disk in
                     ds.disk_set.filter(destroyed__isnull=True)])
        for i in disks - files:
            logging.critical("Image: %s is missing from %s datastore."
                             % (i, ds.path))