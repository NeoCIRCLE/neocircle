from manager.mancelery import celery


@celery.task(name='storagedriver.list')
def list(dir):
    pass


@celery.task(name='storagedriver.create')
def create(disk_desc):
    pass


@celery.task(name='storagedriver.download')
def download(disk_desc, url):
    pass


@celery.task(name='storagedriver.delete')
def delete(path):
    pass


@celery.task(name='storagedriver.delete_dump')
def delete_dump(path):
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


@celery.task(name='storagedriver.make_free_space')
def make_free_space(datastore, percent):
    pass


@celery.task(name='storagedriver.move_to_trash')
def move_to_trash(datastore, disk_path):
    pass


@celery.task(name='storagedriver.get_storage_stat')
def get_storage_stat(path):
    pass
