from manager.mancelery import celery


@celery.task
def deploy(disk, user):
    disk.deploy(task_uuid=deploy.request.id, user=user)


@celery.task
def destroy(disk, user):
    disk.destroy(task_uuid=destroy.request.id, user=user)


@celery.task
def restore(disk, user):
    disk.restore(task_uuid=restore.request.id, user=user)


@celery.task
def create_from_url(Disk, url, params, user):
    Disk.create_from_url(url=url,
                         params=params,
                         task_uuid=create_from_url.request.id,
                         user=user)
