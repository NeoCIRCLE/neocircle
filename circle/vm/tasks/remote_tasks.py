from manager.mancelery import celery


@celery.task(name='vmdriver.create')
def create(params):
    pass


@celery.task(name='vmdriver.suspend')
def stop(params):
    pass


@celery.task(name='vmdriver.resume')
def resume(params):
    pass


@celery.task(name='vmdriver.delete')
def poweroff(params):
    pass


@celery.task(name='vmdriver.shutdown')
def shutdown(params):
    pass


@celery.task(name='vmdriver.reset')
def reset(params):
    pass


@celery.task(name='vmdriver.start')
def restart(params):
    pass


@celery.task(name='vmdriver.reboot')
def reboot(params):
    pass


@celery.task(name='vmdriver.save')
def save(params):
    pass


@celery.task(name='vmdriver.restore')
def restore(params):
    pass


@celery.task(name='vmdriver.migrate')
def migrate(params):
    pass
