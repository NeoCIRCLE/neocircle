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
from vm.tasks.agent_tasks import (restart_networking, change_password,
                                  set_time, set_hostname, start_access_server,
                                  cleanup)
import time


def send_init_commands(instance, act, vm):
    queue = instance.get_remote_queue_name("agent")

    with act.sub_activity('cleanup'):
        cleanup.apply_async(queue=queue, args=(vm, ))
    with act.sub_activity('restart_networking'):
        restart_networking.apply_async(queue=queue, args=(vm, ))
    with act.sub_activity('change_password'):
        change_password.apply_async(queue=queue, args=(vm, instance.pw))
    with act.sub_activity('set_time'):
        set_time.apply_async(queue=queue, args=(vm, time.time()))
    with act.sub_activity('set_hostname'):
        set_hostname.apply_async(
            queue=queue, args=(vm, instance.primary_host.hostname))


@celery.task
def agent_started(vm):
    from vm.models import Instance, instance_activity, InstanceActivity
    instance = Instance.objects.get(id=int(vm.split('-')[-1]))
    initialized = InstanceActivity.objects.filter(
        instance=instance, activity_code='vm.Instance.agent').exists()

    with instance_activity(code_suffix='agent', instance=instance) as act:
        with act.sub_activity('starting'):
            pass
        if not initialized:
            send_init_commands(instance, act, vm)
        with act.sub_activity('start_access_server'):
            queue = instance.get_remote_queue_name("agent")
            start_access_server.apply_async(
                queue=queue, args=(vm, ))


@celery.task
def agent_stopped(vm):
    from vm.models import Instance, InstanceActivity
    instance = Instance.objects.get(id=int(vm.split('-')[-1]))
    qs = InstanceActivity.objects.filter(instance=instance,
                                         activity_code='vm.Instance.agent')
    act = qs.latest('id')
    with act.sub_activity('stopping'):
        pass
