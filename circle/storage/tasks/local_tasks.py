# Copyright 2014 Budapest University of Technology and Economics (BME IK)
#
# This file is part of CIRCLE Cloud.
#
# CIRCLE is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# CIRCLE is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along
# with CIRCLE.  If not, see <http://www.gnu.org/licenses/>.

from manager.mancelery import celery
from celery.contrib.abortable import AbortableTask


@celery.task
def check_queue(storage, queue_id, priority):
    ''' Celery inspect job to check for active workers at queue_id
        return True/False
    '''
    queue_name = storage + "." + queue_id
    if priority is not None:
        queue_name = queue_name + "." + priority
    inspect = celery.control.inspect()
    inspect.timeout = 0.5
    active_queues = inspect.active_queues()
    if active_queues is None:
        return False

    queue_names = (queue['name'] for worker in active_queues.itervalues()
                   for queue in worker)
    return queue_name in queue_names


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
    return disk.restore(task_uuid=restore.request.id, user=user)


@celery.task(base=AbortableTask, bind=True)
def create_from_url(self, **kwargs):
    Disk = kwargs.pop('cls')
    Disk.create_from_url(url=kwargs.pop('url'),
                         task_uuid=self.request.id,
                         abortable_task=self,
                         **kwargs)


@celery.task
def create_empty(Disk, instance, user, params):
    Disk.create_empty(instance, user,
                      task_uuid=create_empty.request.id,
                      **params)
