from manager.mancelery import celery

# TODO: Keep synchronised with Instance funcs


@celery.task
def deploy(instance, user):
    instance.deploy(task_uuid=deploy.request.id, user=user)


@celery.task
def redeploy(instance, user):
    instance.redeploy(task_uuid=redeploy.request.id, user=user)


@celery.task
def destroy(instance, user):
    instance.destroy(task_uuid=destroy.request.id, user=user)


@celery.task
def sleep(instance, user):
    instance.sleep(task_uuid=sleep.request.id, user=user)


@celery.task
def wake_up(instance, user):
    instance.wake_up(task_uuid=wake_up.request.id, user=user)


@celery.task
def shutdown(instance, user):
    instance.shutdown(task_uuid=shutdown.request.id, user=user)


@celery.task
def reset(instance, user):
    instance.reset(task_uuid=reset.request.id, user=user)


@celery.task
def reboot(instance, user):
    instance.reboot(task_uuid=reboot.request.id, user=user)


@celery.task
def migrate(instance, to_node,  user):
    instance.migrate(to_node, task_uuid=migrate.request.id, user=user)
