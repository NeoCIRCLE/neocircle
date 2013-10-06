from manager.mancelery import celery

# TODO: Keep syncronhised with Instance funcs

@celery.task
def deploy(instance, user):
    ''' Call Insance.deploy() from celery task.
    '''
    instance.deploy(task_uuid=deploy.request.id, user=user)


def destroy():
    pass


def save_as():
    pass


def suspend():
    pass


def resume():
    pass


def restart():
    pass


def reset():
    pass


def migrate():
    pass
