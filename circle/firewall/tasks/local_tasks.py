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


def _apply_once(name, queues, task, data):
    """Reload given networking component if needed.
    """

    lockname = "%s_lock" % name
    if not cache.get(lockname):
        return
    cache.delete(lockname)

    data = data()
    for queue in queues:
        try:
            task.apply_async(args=data, queue=queue, expires=60).get(timeout=5)
            logger.info("%s configuration is reloaded. (queue: %s)",
                        name, queue)
        except TimeoutError as e:
            logger.critical('%s (queue: %s)', e, queue)
        except:
            logger.critical('Unhandled exception: queue: %s data: %s',
                            queue, data, exc_info=True)


def get_firewall_queues():
    from firewall.models import Firewall
    retval = []
    for fw in Firewall.objects.all():
        try:
            retval.append(fw.get_remote_queue_name('firewall'))
        except WorkerNotFound:
            logger.critical('Firewall %s is offline', fw.name)
    return list(retval)


@celery.task(ignore_result=True)
def reloadtask_worker():
    from firewall.fw import BuildFirewall, dhcp, dns, ipset, vlan
    from remote_tasks import (reload_dns, reload_dhcp, reload_firewall,
                              reload_firewall_vlan, reload_blacklist)

    firewall_queues = get_firewall_queues()
    dns_queues = [("%s.dns" % i) for i in
                  settings.get('dns_queues', [gethostname()])]

    _apply_once('dns', dns_queues, reload_dns,
                lambda: (dns(), ))
    _apply_once('dhcp', firewall_queues, reload_dhcp,
                lambda: (dhcp(), ))
    _apply_once('firewall', firewall_queues, reload_firewall,
                lambda: (BuildFirewall().build_ipt()))
    _apply_once('firewall_vlan', firewall_queues, reload_firewall_vlan,
                lambda: (vlan(), ))
    _apply_once('blacklist', firewall_queues, reload_blacklist,
                lambda: (list(ipset()), ))


@celery.task
def reloadtask(type='Host', timeout=15):
    reload = {
        'Host': ['dns', 'dhcp', 'firewall'],
        'Record': ['dns'],
        'Domain': ['dns'],
        'Vlan': ['dns', 'dhcp', 'firewall', 'firewall_vlan'],
        'Firewall': ['firewall'],
        'Rule': ['firewall'],
        'SwitchPort': ['firewall_vlan'],
        'EthernetDevice': ['firewall_vlan'],
    }[type]
    logger.info("Reload %s on next periodic iteration applying change to %s.",
                ", ".join(reload), type)
    if all([cache.add("%s_lock" % i, 'true', 30) for i in reload]):
        reloadtask_worker.apply_async(queue='localhost.man', countdown=5)
