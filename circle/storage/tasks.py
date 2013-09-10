import celery
from celery.contrib.methods import task_method

import logging

logger = logging.getLogger(__name__)


class StorageDriver:
    @celery.task(filter=task_method, name='storagedriver.list_disks')
    def list_disks(dir):
        pass

    @celery.task(filter=task_method, name='storagedriver.create_disk')
    def create_disk(disk_desc):
        pass

    @celery.task(filter=task_method, name='storagedriver.delete_disk')
    def delete_disk(json_data):
        # TODO review
        pass

    @celery.task(filter=task_method, name='storagedriver.get_disk')
    def get_disk(json_data):
        # TODO review
        pass
