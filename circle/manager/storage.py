from .mancelery import celery


@celery.task
def deploy(disk, user):
    '''Create new virtual machine from VM class.
    '''
    disk.deploy(task_uuid=deploy.rdiskd, user=user)


def delete():
    pass


def save_as():
    pass
