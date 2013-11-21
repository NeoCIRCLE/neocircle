from celery import Celery
from datetime import timedelta
from kombu import Queue, Exchange
from os import getenv

HOSTNAME = "localhost"

celery = Celery('manager', backend='amqp',
                broker=getenv("AMQP_URI"),
                include=['vm.tasks.local_tasks',
                         'vm.tasks.local_periodic_tasks',
                         'storage.tasks.local_tasks',
                         'firewall.tasks.local_tasks'])

celery.conf.update(
    CELERY_TASK_RESULT_EXPIRES = 300,
    CELERY_QUEUES=(
        Queue(HOSTNAME + '.man', Exchange('manager', type='direct'),
              routing_key="manager"),
        Queue(HOSTNAME + '.monitor', Exchange('monitor', type='direct'),
              routing_key="monitor"),
    ),
    CELERYBEAT_SCHEDULE={
        'firewall.periodic_task': {
            'task': 'firewall.tasks.local_tasks.periodic_task',
            'schedule': timedelta(seconds=5),
            'options': {'queue': 'localhost.man'}
        },
        'vm.periodic_tasks': {
            'task': 'vm.tasks.local_periodic_tasks.update_domain_states',
            'schedule': timedelta(seconds=10),
            'options': {'queue': 'localhost.man'}
        },
    }

)
