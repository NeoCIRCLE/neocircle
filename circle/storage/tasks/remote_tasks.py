from manager.mancelery import celery


@celery.task(name='storagedriver.list_disks')
def list_disks(dir):
    pass


@celery.task(name='storagedriver.create_disk')
def create_disk(disk_desc):
    pass


@celery.task(name='storagedriver.delete_disk')
def delete_disk(json_data):
    pass


@celery.task(name='storagedriver.get_disk')
def get_disk(json_data):
    pass
