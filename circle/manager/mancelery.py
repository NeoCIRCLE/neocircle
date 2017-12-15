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
from celery.schedules import crontab
from datetime import timedelta
from kombu import Queue, Exchange
from os import getenv


HOSTNAME = "localhost"
QUEUE_NAME = HOSTNAME + '.man'
AUTO_MIGRATION_CRONTAB = getenv('AUTO_MIGRATION_CRONTAB', '0 0 * * *')


def crontab_parser(crontab):
    fields = crontab.split(' ')
    return dict(
        minute=fields[0],
        hour=fields[1],
        day_of_month=fields[2],
        month_of_year=fields[3],
        day_of_week=fields[4],
    )


celery = Celery('manager',
                broker=getenv("AMQP_URI"),
                include=['vm.tasks.local_tasks',
                         'vm.tasks.local_periodic_tasks',
                         'vm.tasks.local_agent_tasks',
                         'storage.tasks.local_tasks',
                         'storage.tasks.periodic_tasks',
                         'firewall.tasks.local_tasks',
                         'dashboard.tasks.local_periodic_tasks',
                         ])

celery.conf.update(
    CELERY_RESULT_BACKEND='amqp',
    CELERY_TASK_RESULT_EXPIRES=300,
    CELERY_QUEUES=(
        Queue(HOSTNAME + '.man', Exchange('manager', type='direct'),
              routing_key="manager"),
    ),
    CELERYBEAT_SCHEDULE={
        'storage.periodic_tasks': {
            'task': 'storage.tasks.periodic_tasks.garbage_collector',
            'schedule': timedelta(hours=1),
            'options': {'queue': 'localhost.man'}
        },
        'dashboard.send_email_notifications': {
            'task': 'dashboard.tasks.local_periodic_tasks.'
            'send_email_notifications',
            'schedule': timedelta(hours=24),
            'options': {'queue': 'localhost.man'}
        },
        'vm.local_periodic_tasks': {
            'task': 'vm.tasks.local_periodic_tasks.auto_migrate',
            'schedule': crontab(**crontab_parser(AUTO_MIGRATION_CRONTAB)),
            'options': {'queue': 'localhost.man.slow'},
        },
    }

)


@worker_ready.connect()
def cleanup_tasks(conf=None, **kwargs):
    '''Discard all task and clean up activity.'''
    from vm.models.activity import cleanup
    cleanup(queue_name=QUEUE_NAME)
