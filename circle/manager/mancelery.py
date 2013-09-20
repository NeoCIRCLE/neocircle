from celery import Celery
from kombu import Queue, Exchange
from os import getenv

HOSTNAME = "localhost"

celery = Celery('manager', backend='amqp',
                broker=getenv("AMQP_URI"),
                include=['vm.tasks.local_tasks', 'storage.tasks.local_tasks'])

celery.conf.update(
    CELERY_QUEUES=(
        Queue(HOSTNAME + '.man', Exchange('manager', type='direct'),
              routing_key="manager"),
    )
)
