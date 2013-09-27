from manager.mancelery import celery


@celery.task
def deploy(disk, user):
    disk.deploy(task_uuid=deploy.request.id, user=user)


@celery.task
def delete():
    pass


@celery.task
def save_as():
    pass
