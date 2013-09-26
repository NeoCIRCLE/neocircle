from manager.mancelery import celery


@celery.task(name='storagedriver.list')
def list(dir):
    pass


@celery.task(name='storagedriver.create')
def create(disk_desc):
    pass


@celery.task(name='storagedriver.delete')
def delete(json_data):
    pass


@celery.task(name='storagedriver.snapshot')
def snapshot(json_data):
    pass


@celery.task(name='storagedriver.get')
def get(json_data):
    pass
