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
def deploy(disk, user):
    disk.deploy(task_uuid=deploy.request.id, user=user)


@celery.task
def destroy(disk, user):
    disk.destroy(task_uuid=destroy.request.id, user=user)


@celery.task
def restore(disk, user):
    disk.restore(task_uuid=restore.request.id, user=user)


class create_from_url(AbortableTask):

    def run(self, **kwargs):
        Disk = kwargs['cls']
        url = kwargs['url']
        params = kwargs['params']
        user = kwargs['user']
        Disk.create_from_url(url=url,
                             params=params,
                             task_uuid=create_from_url.request.id,
                             abortable_task=self,
                             user=user)
