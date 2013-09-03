#!/usr/bin/env python

from mancelery import celery
from celery import current_task

import scheduler


@celery.task
def deploy(instance):
    '''Create new virtual machine from VM class.
    '''
    # Get info from scheduler (free space, node with enough cpu and ram)
    current_task.update_state(state='PENDING')
    instance.node = scheduler.get_node()

    # Create hard drives (storage)
    current_task.update_state(state='PREPARE')
    for disk in instance.disks:
        disk.deploy()

    # Create context
    instance.create_context()

    # Create machine (vmdriver)
    current_task.update_state(state='DEPLOY VM')
    instance.deploy_task()

    # Estabilish network connection (vmdriver)
    current_task.update_state(state='DEPLOY NET')
    instance.deploy_net()
    # Resume machine (vmdriver)
    current_task.update_state(state='BOOT')
    instance.resume()
    pass


def delete():
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
