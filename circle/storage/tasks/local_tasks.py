from manager.mancelery import celery


@celery.task
def deploy(disk, user):
    disk.deploy(task_uuid=deploy.request.id, user=user)


@celery.task
def remove(disk, user):
    disk.remove(task_uuid=remove.request.id, user=user)


@celery.task
def save_as():
    pass
