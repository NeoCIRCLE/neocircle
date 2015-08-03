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

from logging import getLogger
from socket import gethostname

import django.conf
from django.core.cache import cache
from celery.exceptions import TimeoutError

from manager.mancelery import celery
from common.models import WorkerNotFound

settings = django.conf.settings.FIREWALL_SETTINGS
logger = getLogger(__name__)


def _apply_once(name, tasks, queues, task, data):
    """Reload given networking component if needed.
    """

    if name not in tasks:
        return

    data = data()
    for queue in queues:
        try:
            task.apply_async(args=data, queue=queue, expires=60).get(timeout=2)
            logger.info("%s configuration is reloaded. (queue: %s)",
                        name, queue)
        except TimeoutError as e:
            logger.critical('%s (queue: %s, task: %s)', e, queue, name)
        except:
            logger.critical('Unhandled exception: queue: %s data: %s task: %s',
                            queue, data, name, exc_info=True)


def get_firewall_queues():
    from firewall.models import Firewall
    retval = []
    for fw in Firewall.objects.all():
        try:
            retval.append(fw.get_remote_queue_name('firewall'))
        except WorkerNotFound:
            logger.critical('Firewall %s is offline', fw.name)
    return list(retval)


@celery.task
def reloadtask_worker():
    from firewall.fw import BuildFirewall, dhcp, dns, ipset, vlan
    from remote_tasks import (reload_dns, reload_dhcp, reload_firewall,
                              reload_firewall_vlan, reload_blacklist)

    tasks = []
    for i in ('dns', 'dhcp', 'firewall', 'firewall_vlan', 'blacklist'):
        lockname = "%s_lock" % i
        if cache.get(lockname):
            tasks.append(i)
        cache.delete(lockname)

    logger.info("reloadtask_worker: Reload %s", ", ".join(tasks))

    firewall_queues = get_firewall_queues()
    dns_queues = [("%s.dns" % i) for i in
                  settings.get('dns_queues', [gethostname()])]

    _apply_once('dns', tasks, dns_queues, reload_dns,
                lambda: (dns(), ))
    _apply_once('dhcp', tasks, firewall_queues, reload_dhcp,
                lambda: (dhcp(), ))
    _apply_once('firewall', tasks, firewall_queues, reload_firewall,
                lambda: (BuildFirewall().build_ipt()))
    _apply_once('firewall_vlan', tasks, firewall_queues, reload_firewall_vlan,
                lambda: (vlan(), ))
    _apply_once('blacklist', tasks, firewall_queues, reload_blacklist,
                lambda: (list(ipset()), ))


@celery.task
def reloadtask(type='Host', timeout=15, sync=False):
    reload = {
        'Host': ['dns', 'dhcp', 'firewall'],
        'Record': ['dns'],
        'Domain': ['dns'],
        'Vlan': ['dns', 'dhcp', 'firewall', 'firewall_vlan'],
        'Firewall': ['firewall'],
        'Rule': ['firewall'],
        'SwitchPort': ['firewall_vlan'],
        'EthernetDevice': ['firewall_vlan'],
        'BlacklistItem': ['blacklist'],
    }[type]
    logger.info("Reload %s on next periodic iteration applying change to %s.",
                ", ".join(reload), type)
    if all([cache.add("%s_lock" % i, 'true', 30) for i in reload]):
        res = reloadtask_worker.apply_async(queue='localhost.man', countdown=5)
        if sync:
            res.get(15)
