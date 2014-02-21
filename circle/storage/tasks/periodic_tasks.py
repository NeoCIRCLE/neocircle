from storage.models import DataStore
import os
from django.utils import timezone
from datetime import timedelta
from manager.mancelery import celery
import logging

logger = logging.getLogger(__name__)


@celery.task
def garbage_collector():
    logging.warning("Deletable disks:")
    for ds in DataStore.objects.all():
        one_week_before = timezone.now() - timedelta(days=7)
        file_list = os.listdir(ds.path)
        disk_list = [disk.filename for disk in
                     ds.disk_set.filter(destroyed__lt=one_week_before)]
        for i in set(file_list).intersection(disk_list):
            abs_path = ds.path + "/" + i
            logging.warning(i + " - " +
                            str(os.path.getsize(abs_path) / 1024 / 1024))
            #os.unlink(abs_path)

    logging.warning("Orphan disks:")
    for ds in DataStore.objects.all():
        one_week_before = timezone.now() - timedelta(days=7)
        file_list = os.listdir(ds.path)
        disk_list = [disk.filename for disk in ds.disk_set.all()]
        for i in set(file_list).difference(disk_list):
            if "dump" not in i:
                abs_path = ds.path + "/" + i
                logging.warning(i + " - " +
                                str(os.path.getsize(abs_path) / 1024 / 1024))

    logging.warning("Missing disks:")
    for ds in DataStore.objects.all():
        one_week_before = timezone.now() - timedelta(days=7)
        file_list = os.listdir(ds.path)
        disk_list = [disk.filename for disk in
                     ds.disk_set.filter(destroyed__isnull=False)]
        for i in set(disk_list).difference(file_list):
            logging.warning(i)
