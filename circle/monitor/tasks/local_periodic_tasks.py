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

import logging
import requests
from time import time

from django.conf import settings
from manager.mancelery import celery

from vm.tasks.vm_tasks import check_queue
from firewall.tasks.remote_tasks import check_queue as check_queue_fw
from vm.models import Node, InstanceTemplate
from firewall.models import Firewall
from storage.models import DataStore
from monitor.client import Client

logger = logging.getLogger(__name__)


@celery.task(ignore_result=True)
def measure_response_time():
    try:
        r = requests.get(settings.DJANGO_URL, verify=False,
                         timeout=0.5)
    except requests.exceptions.Timeout:
        return
    total_miliseconds = (
        r.elapsed.seconds * 10**6 +
        r.elapsed.microseconds) / 1000

    Client().send([
        "%(name)s %(val)d %(time)s" % {
            'name': "portal.response_time",
            'val': total_miliseconds,
            'time': time(),
        }
    ])


@celery.task(ignore_result=True)
def check_celery_queues():
    def graphite_string(component, hostname, celery, is_alive, time): return (
        "%s.%s.celery-queues.%s %d %s" % (
            component, hostname, celery, 1 if is_alive else 0, time)
    )

    metrics = []
    for n in Node.objects.all():  # disabled, offline nodes?
        for s in ["fast", "slow"]:
            is_queue_alive = check_queue(n.host.hostname, "vm", s)

            metrics.append(graphite_string("circle", n.host.hostname,
                                           "vm-" + s, is_queue_alive, time()))
        is_net_queue_alive = check_queue(n.host.hostname, "net", "fast")
        metrics.append(graphite_string("circle", n.host.hostname,
                                       "net-fast", is_net_queue_alive, time()))

        is_agent_queue_alive = check_queue(n.host.hostname, "agent")
        metrics.append(graphite_string("circle", n.host.hostname, "agent",
                                       is_agent_queue_alive, time()))

    for ds in DataStore.objects.all():
        for s in ["fast", "slow"]:
            is_queue_alive = check_queue(ds.hostname, "vm", s)

            metrics.append(graphite_string("storage", ds.hostname,
                                           "storage-" + s, is_queue_alive,
                                           time()))

    for fw in Firewall.objects.all():
        is_queue_alive = check_queue_fw(fw.name, "firewall", None)
        metrics.append(graphite_string(
            "firewall", fw.name, "firewall", is_queue_alive, time()))

    Client().send(metrics)


@celery.task(ignore_result=True)
def instance_per_template():
    def graphite_string(pk, state, val, time): return (
        "template.%d.instances.%s %d %s" % (
            pk, state, val, time)
    )

    metrics = []
    for t in InstanceTemplate.objects.all():
        base = t.instance_set.filter(destroyed_at=None)
        running = base.filter(status="RUNNING").count()
        not_running = base.exclude(status="RUNNING").count()
        metrics.append(graphite_string(t.pk, "running", running, time()))
        metrics.append(graphite_string(t.pk, "not_running", not_running,
                                       time()))

    Client().send(metrics)


@celery.task(ignore_result=True)
def allocated_memory():
    def graphite_string(hostname, val, time): return (
        "circle.%s.memory.allocated %d %s" % (
            hostname, val, time)
    )

    metrics = []
    for n in Node.objects.all():
        print n.allocated_ram
        metrics.append(graphite_string(
            n.host.hostname, n.allocated_ram, time()))

    Client().send(metrics)
