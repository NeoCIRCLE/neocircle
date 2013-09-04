#!/usr/bin/env python

from mancelery import celery


@celery.task
def deploy(instance):
    '''Create new virtual machine from VM class.
    '''
    instance.deploy(task_uuid=deploy.request.id)


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
