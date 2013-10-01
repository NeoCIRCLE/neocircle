from manager.mancelery import celery


@celery.task(name='netdriver.create')
def create(params):
    pass


@celery.task(name='netdriver.delete')
def delete(params):
    pass
