#!/usr/bin/env python

from celery import Celery, task
import subprocess
import time, re
import socket
import sys

BROKER_URL = 'amqp://nyuszi:teszt@localhost:5672/django'
try:
    from local_settings import *
except:
    pass
CELERY_CREATE_MISSING_QUEUES=True
celery = Celery('tasks', broker=BROKER_URL)


def main(argv):
    celery.send_task('one.tasks.UpdateInstanceStateTask', [ int(sys.argv[1]),
        ], queue='local')

if __name__ == "__main__":
    main(sys.argv)
