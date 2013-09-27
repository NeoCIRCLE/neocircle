from manager.mancelery import celery


@celery.task(name='storagedriver.list')
def list(dir):
    pass


@celery.task(name='storagedriver.create')
def create(disk_desc):
    pass


@celery.task(name='storagedriver.delete')
def delete(path):
    pass


@celery.task(name='storagedriver.snapshot')
def snapshot(disk_desc):
    pass


@celery.task(name='storagedriver.get')
def get(path):
    pass


@celery.task(name='storagedriver.merge')
def merge(src_disk_desc, dst_disk_desc):
    pass
