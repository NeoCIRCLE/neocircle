import celery
from celery.contrib.methods import task_method

import logging

logger = logging.getLogger(__name__)


class StorageDriver:
    @celery.task(filter=task_method, name='storagedriver.list_disks')
    def list_disks():
        pass

    @celery.task(filter=task_method, name='storagedriver.create_disk')
    def create_disk(json_data):
        pass

    @celery.task(filter=task_method, name='storagedriver.delete_disk')
    def delete_disk(json_data):
        pass

    @celery.task(filter=task_method, name='storagedriver.get_disk')
    def get_disk(json_data):
        pass
