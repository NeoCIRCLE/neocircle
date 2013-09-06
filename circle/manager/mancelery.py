from celery import Celery
from kombu import Queue, Exchange
from socket import gethostname


HOSTNAME = gethostname()

celery = Celery('manager', backend='amqp',
                broker='amqp://cloud:test@10.9.1.31/vmdriver',
                include=['vmdriver_stub'])

celery.conf.update(
    CELERY_QUEUES=(
        Queue(HOSTNAME + '.man', Exchange(
            'manager', type='direct'), routing_key="manager"),
    )
)
