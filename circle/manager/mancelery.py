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
from datetime import timedelta
from kombu import Queue, Exchange
from os import getenv

HOSTNAME = "localhost"
CACHE_URI = getenv("CACHE_URI", "pylibmc://127.0.0.1:11211/")

celery = Celery('manager',
                broker=getenv("AMQP_URI"),
                include=['vm.tasks.local_tasks',
                         'vm.tasks.local_periodic_tasks',
                         'vm.tasks.local_agent_tasks',
                         'storage.tasks.local_tasks',
                         'storage.tasks.periodic_tasks',
                         'firewall.tasks.local_tasks', ])

celery.conf.update(
    CELERY_RESULT_BACKEND='cache',
    CELERY_CACHE_BACKEND=CACHE_URI,
    CELERY_TASK_RESULT_EXPIRES=300,
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
        'vm.update_domain_states': {
            'task': 'vm.tasks.local_periodic_tasks.update_domain_states',
            'schedule': timedelta(seconds=10),
            'options': {'queue': 'localhost.man'}
        },
        'vm.garbage_collector': {
            'task': 'vm.tasks.local_periodic_tasks.garbage_collector',
            'schedule': timedelta(minutes=10),
            'options': {'queue': 'localhost.man'}
        },
        'storage.periodic_tasks': {
            'task': 'storage.tasks.periodic_tasks.garbage_collector',
            'schedule': timedelta(hours=1),
            'options': {'queue': 'localhost.man'}
        },
    }

)
