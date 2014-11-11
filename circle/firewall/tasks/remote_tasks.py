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

from manager.mancelery import celery


def check_queue(firewall, queue_id, priority):
    ''' Celery inspect job to check for active workers at queue_id
        return True/False
    '''
    queue_name = firewall + "." + queue_id
    if priority is not None:
        queue_name = queue_name + "." + priority
    inspect = celery.control.inspect()
    inspect.timeout = 0.1
    active_queues = inspect.active_queues()
    if active_queues is None:
        return False

    queue_names = (queue['name'] for worker in active_queues.itervalues()
                   for queue in worker)
    return queue_name in queue_names


@celery.task(name='firewall.reload_dns')
def reload_dns(data):
    pass


@celery.task(name='firewall.reload_firewall')
def reload_firewall(data4, data6):
    pass


@celery.task(name='firewall.reload_firewall_vlan')
def reload_firewall_vlan(data):
    pass


@celery.task(name='firewall.reload_dhcp')
def reload_dhcp(data):
    pass


@celery.task(name='firewall.reload_blacklist')
def reload_blacklist(data):
    pass


@celery.task(name='firewall.get_dhcp_clients')
def get_dhcp_clients():
    pass
