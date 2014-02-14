from logging import getLogger
from socket import gethostname

import django.conf
from django.core.cache import cache

from manager.mancelery import celery

settings = django.conf.settings.FIREWALL_SETTINGS
logger = getLogger(__name__)


def _apply_once(name, queues, task, data):
    """Reload given networking component if needed.
    """

    lockname = "%s_lock" % name
    if not cache.get(lockname):
        return
    cache.delete(lockname)

    for queue in queues:
        task.apply_async(args=data, queue=queue)
    logger.info("%s configuration is reloaded.", name)


@celery.task(ignore_result=True)
def periodic_task():
    from firewall.fw import Firewall, dhcp, dns, ipset, vlan
    from remote_tasks import (reload_dns, reload_dhcp, reload_firewall,
                              reload_firewall_vlan, reload_blacklist)

    firewall_queues = [("%s.firewall" % i) for i in
                       settings.get('firewall_queues', [gethostname()])]
    dns_queues = [("%s.dns" % i) for i in
                  settings.get('dns_queues', [gethostname()])]

    _apply_once('dns', dns_queues, reload_dns,
                lambda: (dns(), ))
    _apply_once('dhcp', firewall_queues, reload_dhcp,
                lambda: (dhcp(), ))
    _apply_once('firewall', firewall_queues, reload_firewall,
                lambda: (Firewall(proto=4).get(), Firewall(proto=6).get()))
    _apply_once('firewall_vlan', firewall_queues, reload_firewall_vlan,
                lambda: (vlan(), ))
    _apply_once('blacklist', firewall_queues, reload_blacklist,
                lambda: (list(ipset()), ))


@celery.task
def reloadtask(type='Host'):
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
    for i in reload:
        cache.add("%s_lock" % i, "true", 30)
