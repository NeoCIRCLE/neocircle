from manager.manager import celery


@celery.task(name='vmdriver.create')
def create(parameters):
    pass
