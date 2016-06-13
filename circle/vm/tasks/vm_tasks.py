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

from django.core.cache import cache
from logging import getLogger

from manager.mancelery import celery

logger = getLogger(__name__)


def check_queue(node_hostname, queue_id, priority=None):
    """True if the queue is alive.

    Example: check_queue('node01', 'vm', 'slow'):
    :param node_hostname: Short hostname of the node.
    :param queue_id: Queue identifier (eg. vm).
    :param priority: can be 'slow', 'fast' or None
    """
    # drivers = ['vmdriver', 'netdriver', 'agentdriver']
    # worker_list = [node_hostname + "." + d for d in drivers]
    queue_name = node_hostname + "." + queue_id
    if priority is not None:
        queue_name = queue_name + "." + priority
    active_queues = get_queues()
    if active_queues is None:
        return False
    queue_names = (queue['name'] for worker in active_queues.itervalues()
                   for queue in worker)
    return queue_name in queue_names


def get_queues():
    """Get active celery queues.

    Returns a dictionary whose entries are (worker name;list of queues) pairs,
    where queues are represented by dictionaries.
    Result is cached for 10 seconds!
    """
    key = __name__ + u'queues'
    result = cache.get(key)
    if result is None:
        inspect = celery.control.inspect()
        inspect.timeout = 0.5
        result = inspect.active_queues()
        logger.debug('Queue list of length %d cached.', len(result))
        cache.set(key, result, 10)
    return result


@celery.task(name='vmdriver.attach_disk')
def attach_disk(vm, disk):
    pass


@celery.task(name='vmdriver.detach_disk')
def detach_disk(vm, disk):
    pass


@celery.task(name='vmdriver.attach_network')
def attach_network(vm, net):
    pass


@celery.task(name='vmdriver.detach_network')
def detach_network(vm, net):
    pass


@celery.task(name='vmdriver.create')
def deploy(params):
    pass


@celery.task(name='vmdriver.delete')
def destroy(params):
    pass


@celery.task(name='vmdriver.save')
def sleep(params):
    pass


@celery.task(name='vmdriver.restore')
def wake_up(params):
    pass


@celery.task(name='vmdriver.suspend')
def suspend(params):
    pass


@celery.task(name='vmdriver.resume')
def resume(params):
    pass


@celery.task(name='vmdriver.shutdown')
def shutdown(params):
    pass


@celery.task(name='vmdriver.reset')
def reset(params):
    pass


@celery.task(name='vmdriver.reboot')
def reboot(params):
    pass


@celery.task(name='vmdriver.migrate')
def migrate(params):
    pass


@celery.task(name='vmdriver.resize_disk')
def resize_disk(params):
    pass


@celery.task(name='vmdriver.domain_info')
def domain_info(params):
    pass


@celery.task(name='vmdriver.list_domains')
def list_domains(params):
    pass


@celery.task(name='vmdriver.list_domains_info')
def list_domains_info(params):
    pass


@celery.task(name='vmdriver.ping')
def ping(params):
    pass


@celery.task(name='vmdriver.get_core_num')
def get_core_num(params):
    pass


@celery.task(name='vmdriver.get_architecture')
def get_architecture():
    pass


@celery.task(name='vmdriver.get_ram_size')
def get_ram_size(params):
    pass


@celery.task(name='vmdriver.get_info')
def get_info(params):
    pass


@celery.task(name='vmdriver.get_node_metrics')
def get_node_metrics(params):
    pass


@celery.task(name='vmdriver.screenshot')
def screenshot(params):
    pass


@celery.task(name='vmdriver.refresh_secret')
def refresh_credential(user, secret):
    pass
