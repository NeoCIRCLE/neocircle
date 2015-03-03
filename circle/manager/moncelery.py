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

from celery import Celery
from celery.signals import worker_ready
from datetime import timedelta
from kombu import Queue, Exchange
from os import getenv

HOSTNAME = "localhost"
QUEUE_NAME = HOSTNAME + '.monitor'

celery = Celery('monitor',
                broker=getenv("AMQP_URI"),
                include=['vm.tasks.local_periodic_tasks',
                         'monitor.tasks.local_periodic_tasks',
                         ])

celery.conf.update(
    CELERY_RESULT_BACKEND='amqp',
    CELERY_TASK_RESULT_EXPIRES=300,
    CELERY_QUEUES=(
        Queue(QUEUE_NAME, Exchange('monitor', type='direct'),
              routing_key="monitor"),
    ),
    CELERYBEAT_SCHEDULE={
        'vm.update_domain_states': {
            'task': 'vm.tasks.local_periodic_tasks.update_domain_states',
            'schedule': timedelta(seconds=10),
            'options': {'queue': 'localhost.monitor'}
        },
        'monitor.measure_response_time': {
            'task': 'monitor.tasks.local_periodic_tasks.'
                    'measure_response_time',
            'schedule': timedelta(seconds=30),
            'options': {'queue': 'localhost.monitor'}
        },
        'monitor.check_celery_queues': {
            'task': 'monitor.tasks.local_periodic_tasks.'
                    'check_celery_queues',
            'schedule': timedelta(seconds=60),
            'options': {'queue': 'localhost.monitor'}
        },
        'monitor.instance_per_template': {
            'task': 'monitor.tasks.local_periodic_tasks.'
                    'instance_per_template',
            'schedule': timedelta(seconds=30),
            'options': {'queue': 'localhost.monitor'}
        },
        'monitor.allocated_memory': {
            'task': 'monitor.tasks.local_periodic_tasks.'
                    'allocated_memory',
            'schedule': timedelta(seconds=30),
            'options': {'queue': 'localhost.monitor'}
        },
    }

)


@worker_ready.connect()
def cleanup_tasks(conf=None, **kwargs):
    '''Discard all task and clean up activity.'''
    from vm.models.activity import cleanup
    cleanup(queue_name=QUEUE_NAME)
