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

from common.models import create_readable
from manager.mancelery import celery
from vm.tasks.agent_tasks import (restart_networking, change_password,
                                  set_time, set_hostname, start_access_server,
                                  cleanup, update, append,
                                  change_ip, update_legacy)
from firewall.models import Host

import time
import os
from base64 import encodestring
from hashlib import md5
from StringIO import StringIO
from tarfile import TarFile, TarInfo
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import ugettext_noop
from celery.result import TimeoutError
from monitor.client import Client


def send_init_commands(instance, act):
    vm = instance.vm_name
    queue = instance.get_remote_queue_name("agent")
    with act.sub_activity('cleanup', readable_name=ugettext_noop('cleanup')):
        cleanup.apply_async(queue=queue, args=(vm, ))
    with act.sub_activity('change_password',
                          readable_name=ugettext_noop('change password')):
        change_password.apply_async(queue=queue, args=(vm, instance.pw))
    with act.sub_activity('set_time', readable_name=ugettext_noop('set time')):
        set_time.apply_async(queue=queue, args=(vm, time.time()))
    with act.sub_activity('set_hostname',
                          readable_name=ugettext_noop('set hostname')):
        set_hostname.apply_async(
            queue=queue, args=(vm, instance.short_hostname))


def send_networking_commands(instance, act):
    queue = instance.get_remote_queue_name("agent")
    with act.sub_activity('change_ip',
                          readable_name=ugettext_noop('change ip')):
        change_ip.apply_async(queue=queue, args=(
            instance.vm_name, ) + get_network_configs(instance))
    with act.sub_activity('restart_networking',
                          readable_name=ugettext_noop('restart networking')):
        restart_networking.apply_async(queue=queue, args=(instance.vm_name, ))


def create_linux_tar():
    def exclude(tarinfo):
        ignored = ('./.', './misc', './windows')
        if any(tarinfo.name.startswith(x) for x in ignored):
            return None
        else:
            return tarinfo

    f = StringIO()

    with TarFile.open(fileobj=f, mode='w:gz') as tar:
        agent_path = os.path.join(settings.AGENT_DIR, "agent-linux")
        tar.add(agent_path, arcname='.', filter=exclude)

        version_fileobj = StringIO(settings.AGENT_VERSION)
        version_info = TarInfo(name='version.txt')
        version_info.size = len(version_fileobj.buf)
        tar.addfile(version_info, version_fileobj)

    return encodestring(f.getvalue()).replace('\n', '')


def create_windows_tar():
    f = StringIO()

    agent_path = os.path.join(settings.AGENT_DIR, "agent-win")
    with TarFile.open(fileobj=f, mode='w|gz') as tar:
        tar.add(agent_path, arcname='.')

        version_fileobj = StringIO(settings.AGENT_VERSION)
        version_info = TarInfo(name='version.txt')
        version_info.size = len(version_fileobj.buf)
        tar.addfile(version_info, version_fileobj)

    return encodestring(f.getvalue()).replace('\n', '')


@celery.task
def agent_started(vm, version=None, system=None):
    from vm.models import Instance, instance_activity, InstanceActivity
    instance = Instance.objects.get(id=int(vm.split('-')[-1]))
    queue = instance.get_remote_queue_name("agent")
    initialized = instance.activity_log.filter(
        activity_code='vm.Instance.agent.cleanup').exists()

    with instance_activity(code_suffix='agent',
                           readable_name=ugettext_noop('agent'),
                           concurrency_check=False,
                           instance=instance) as act:
        with act.sub_activity('starting',
                              readable_name=ugettext_noop('starting')):
            pass

        for i in InstanceActivity.objects.filter(
                (Q(activity_code__endswith='.os_boot') |
                 Q(activity_code__endswith='.agent_wait')),
                instance=instance, finished__isnull=True):
            i.finish(True)

        if version and version != settings.AGENT_VERSION:
            try:
                update_agent(instance, act, system, settings.AGENT_VERSION)
            except TimeoutError:
                pass
            else:
                act.sub_activity('agent_wait', readable_name=ugettext_noop(
                    "wait agent restarting"), interruptible=True)
                return  # agent is going to restart

        if not initialized:
            measure_boot_time(instance)
            send_init_commands(instance, act)

        send_networking_commands(instance, act)
        with act.sub_activity('start_access_server',
                              readable_name=ugettext_noop(
                                  'start access server')):
            start_access_server.apply_async(queue=queue, args=(vm, ))


def measure_boot_time(instance):
    if not instance.template:
        return

    from vm.models import InstanceActivity
    deploy_time = InstanceActivity.objects.filter(
        instance=instance, activity_code="vm.Instance.deploy"
    ).latest("finished").finished

    total_boot_time = (timezone.now() - deploy_time).total_seconds()

    Client().send([
        "template.%(pk)d.boot_time %(val)f %(time)s" % {
            'pk': instance.template.pk,
            'val': total_boot_time,
            'time': time.time(),
        }
    ])


@celery.task
def agent_stopped(vm):
    from vm.models import Instance, InstanceActivity
    from vm.models.activity import ActivityInProgressError
    instance = Instance.objects.get(id=int(vm.split('-')[-1]))
    qs = InstanceActivity.objects.filter(instance=instance,
                                         activity_code='vm.Instance.agent')
    act = qs.latest('id')
    try:
        with act.sub_activity('stopping',
                              readable_name=ugettext_noop('stopping')):
            pass
    except ActivityInProgressError:
        pass


def get_network_configs(instance):
    interfaces = {}
    for host in Host.objects.filter(interface__instance=instance):
        interfaces[str(host.mac)] = host.get_network_config()
    return (interfaces, settings.FIREWALL_SETTINGS['rdns_ip'])


def update_agent(instance, act=None, system=None, version=None):
    if act:
        act = act.sub_activity(
            'update',
            readable_name=create_readable(
                ugettext_noop('update to %(version)s'),
                version=settings.AGENT_VERSION))
    else:
        from vm.models import instance_activity
        act = instance_activity(
            code_suffix='agent.update', instance=instance,
            readable_name=create_readable(
                ugettext_noop('update agent to %(version)s'),
                version=settings.AGENT_VERSION))
    with act:
        queue = instance.get_remote_queue_name("agent")
        if system == "Windows":
            executable = os.listdir(os.path.join(settings.AGENT_DIR,
                                                 "agent-win"))[0]
            # executable = "agent-winservice-%(version)s.exe" % {
            #   'version': version}
            data = create_windows_tar()
        elif system == "Linux":
            executable = ""
            data = create_linux_tar()
        else:
            executable = ""
            # Legacy update method
            return update_legacy.apply_async(
                queue=queue,
                args=(instance.vm_name, create_linux_tar())
            ).get(timeout=60)

        checksum = md5(data).hexdigest()
        chunk_size = 1024 * 1024
        chunk_number = 0
        index = 0
        filename = version + ".tar"
        while True:
            chunk = data[index:index+chunk_size]
            if chunk:
                append.apply_async(
                    queue=queue,
                    args=(instance.vm_name, chunk,
                          filename, chunk_number)).get(timeout=60)
                index = index + chunk_size
                chunk_number = chunk_number + 1
            else:
                update.apply_async(
                    queue=queue,
                    args=(instance.vm_name, filename, executable, checksum)
                ).get(timeout=60)
                break
