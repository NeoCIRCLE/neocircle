#!/usr/bin/env python

from mancelery import celery


@celery.task
def create_vm():
    '''Create new virtual machine from VM class.
    '''
    # Get info from scheduler (free sapce, node with enough cpu and ram)

    # Create hard drives (storage)

    # Create machine (vmdriver)
    # Estabilish network connection (vmdriver)
    # Resume machine (vmdriver)
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
