from manager.mancelery import celery
from celery.contrib.abortable import AbortableTask


@celery.task
def check_queue(storage, queue_id):
    ''' Celery inspect job to check for active workers at queue_id
        return True/False
    '''
    drivers = ['storage', 'download']
    worker_list = [storage + "." + d for d in drivers]
    queue_name = storage + "." + queue_id
    # v is List of List of queues dict
    active_queues = celery.control.inspect(worker_list).active_queues()
    if active_queues is not None:
        node_workers = [v for k, v in active_queues.iteritems()]
        for worker in node_workers:
            for queue in worker:
                if queue['name'] == queue_name:
                    return True
    return False


@celery.task
def save_as(disk, timeout, user):
    disk.save_disk_as(task_uuid=save_as.request.id, user=user,
                      disk=disk, timeout=timeout)


@celery.task
def clone(disk, new_disk, timeout, user):
    disk.clone(task_uuid=save_as.request.id, user=user,
               disk=new_disk, timeout=timeout)


@celery.task
def deploy(disk, user):
    disk.deploy(task_uuid=deploy.request.id, user=user)


@celery.task
def destroy(disk, user):
    disk.destroy(task_uuid=destroy.request.id, user=user)


@celery.task
def restore(disk, user):
    disk.restore(task_uuid=restore.request.id, user=user)


class CreateFromURLTask(AbortableTask):

    def __init__(self):
        self.bind(celery)

    def run(self, **kwargs):
        Disk = kwargs.pop('cls')
        Disk.create_from_url(url=kwargs.pop('url'),
                             task_uuid=create_from_url.request.id,
                             abortable_task=self,
                             **kwargs)
create_from_url = CreateFromURLTask()


@celery.task
def create_empty(Disk, instance, user, params):
    Disk.create_empty(instance, user,
                      task_uuid=create_empty.request.id,
                      **params)
