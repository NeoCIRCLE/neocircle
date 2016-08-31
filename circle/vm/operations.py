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

from __future__ import absolute_import, unicode_literals
from base64 import encodestring
from hashlib import md5
from logging import getLogger
import os
from re import search
from string import ascii_lowercase
from StringIO import StringIO
from tarfile import TarFile, TarInfo
import time
from urlparse import urlsplit

from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _, ugettext_noop
from django.conf import settings
from django.db.models import Q

from sizefield.utils import filesizeformat

from celery.contrib.abortable import AbortableAsyncResult
from celery.exceptions import TimeLimitExceeded, TimeoutError

from common.models import (
    create_readable, humanize_exception, HumanReadableException
)
from common.operations import Operation, register_operation, SubOperationMixin
from manager.scheduler import SchedulerError
from .tasks.local_tasks import (
    abortable_async_instance_operation, abortable_async_node_operation,
)
from .models import (
    Instance, InstanceActivity, InstanceTemplate, Interface, Node,
    NodeActivity, pwgen
)
from .tasks import agent_tasks, vm_tasks

from dashboard.store_api import Store, NoStoreException
from firewall.models import Host
from monitor.client import Client
from storage.tasks import storage_tasks

logger = getLogger(__name__)


class RemoteOperationMixin(object):

    remote_timeout = 30

    def _operation(self, **kwargs):
        args = self._get_remote_args(**kwargs)
        return self.task.apply_async(
            args=args, queue=self._get_remote_queue()
        ).get(timeout=self.remote_timeout)

    def check_precond(self):
        super(RemoteOperationMixin, self).check_precond()
        self._get_remote_queue()


class AbortableRemoteOperationMixin(object):
    remote_step = property(lambda self: self.remote_timeout / 10)

    def _operation(self, task, **kwargs):
        args = self._get_remote_args(**kwargs),
        remote = self.task.apply_async(
            args=args, queue=self._get_remote_queue())
        for i in xrange(0, self.remote_timeout, self.remote_step):
            try:
                return remote.get(timeout=self.remote_step)
            except TimeoutError as e:
                if task is not None and task.is_aborted():
                    AbortableAsyncResult(remote.id).abort()
                    raise humanize_exception(ugettext_noop(
                        "Operation aborted by user."), e)
        raise TimeLimitExceeded()


class InstanceOperation(Operation):
    acl_level = 'owner'
    async_operation = abortable_async_instance_operation
    host_cls = Instance
    concurrency_check = True
    accept_states = None
    deny_states = None
    resultant_state = None

    def __init__(self, instance):
        super(InstanceOperation, self).__init__(subject=instance)
        self.instance = instance

    def check_precond(self):
        if self.instance.destroyed_at:
            raise self.instance.InstanceDestroyedError(self.instance)
        if self.accept_states:
            if self.instance.status not in self.accept_states:
                logger.debug("precond failed for %s: %s not in %s",
                             unicode(self.__class__),
                             unicode(self.instance.status),
                             unicode(self.accept_states))
                raise self.instance.WrongStateError(self.instance)
        if self.deny_states:
            if self.instance.status in self.deny_states:
                logger.debug("precond failed for %s: %s in %s",
                             unicode(self.__class__),
                             unicode(self.instance.status),
                             unicode(self.accept_states))
                raise self.instance.WrongStateError(self.instance)

    def check_auth(self, user):
        if not self.instance.has_level(user, self.acl_level):
            raise humanize_exception(ugettext_noop(
                "%(acl_level)s level is required for this operation."),
                PermissionDenied(), acl_level=self.acl_level)

        super(InstanceOperation, self).check_auth(user=user)

        if (self.instance.node and not self.instance.node.online and
                not user.is_superuser):
            raise self.instance.WrongStateError(self.instance)

    def create_activity(self, parent, user, kwargs):
        name = self.get_activity_name(kwargs)
        if parent:
            if parent.instance != self.instance:
                raise ValueError("The instance associated with the specified "
                                 "parent activity does not match the instance "
                                 "bound to the operation.")
            if parent.user != user:
                raise ValueError("The user associated with the specified "
                                 "parent activity does not match the user "
                                 "provided as parameter.")

            return parent.create_sub(
                code_suffix=self.get_activity_code_suffix(),
                readable_name=name, resultant_state=self.resultant_state)
        else:
            return InstanceActivity.create(
                code_suffix=self.get_activity_code_suffix(),
                instance=self.instance,
                readable_name=name, user=user,
                concurrency_check=self.concurrency_check,
                resultant_state=self.resultant_state)

    def is_preferred(self):
        """If this is the recommended op in the current state of the instance.
        """
        return False


class RemoteInstanceOperation(RemoteOperationMixin, InstanceOperation):

    remote_queue = ('vm', 'fast')

    def _get_remote_queue(self):
        return self.instance.get_remote_queue_name(*self.remote_queue)

    def _get_remote_args(self, **kwargs):
        return [self.instance.vm_name]


class EnsureAgentMixin(object):
    accept_states = ('RUNNING', )

    def check_precond(self):
        super(EnsureAgentMixin, self).check_precond()

        last_boot_time = self.instance.activity_log.filter(
            succeeded=True, activity_code__in=(
                "vm.Instance.deploy", "vm.Instance.reset",
                "vm.Instance.reboot")).latest("finished").finished

        try:
            InstanceActivity.objects.filter(
                activity_code="vm.Instance.agent.starting",
                started__gt=last_boot_time, instance=self.instance
            ).latest("started")
        except InstanceActivity.DoesNotExist:  # no agent since last boot
            raise self.instance.NoAgentError(self.instance)


class RemoteAgentOperation(EnsureAgentMixin, RemoteInstanceOperation):
    remote_queue = ('agent', )
    concurrency_check = False


@register_operation
class AddInterfaceOperation(InstanceOperation):
    id = 'add_interface'
    name = _("add interface")
    description = _("Add a new network interface for the specified VLAN to "
                    "the VM.")
    required_perms = ()
    accept_states = ('STOPPED', 'PENDING', 'RUNNING')

    def rollback(self, net, activity):
        with activity.sub_activity(
            'destroying_net',
                readable_name=ugettext_noop("destroy network (rollback)")):
            net.destroy()
            net.delete()

    def _operation(self, activity, user, system, vlan, managed=None):
        if not vlan.has_level(user, 'user'):
            raise humanize_exception(ugettext_noop(
                "User acces to vlan %(vlan)s is required."),
                PermissionDenied(), vlan=vlan)
        if managed is None:
            managed = vlan.managed

        net = Interface.create(base_activity=activity, instance=self.instance,
                               managed=managed, owner=user, vlan=vlan)

        if self.instance.is_running:
            try:
                self.instance._attach_network(
                    interface=net, parent_activity=activity)
            except Exception as e:
                if hasattr(e, 'libvirtError'):
                    self.rollback(net, activity)
                raise
            net.deploy()
            self.instance._change_ip(parent_activity=activity)
            self.instance._restart_networking(parent_activity=activity)

    def get_activity_name(self, kwargs):
        return create_readable(ugettext_noop("add %(vlan)s interface"),
                               vlan=kwargs['vlan'])


@register_operation
class CreateDiskOperation(InstanceOperation):

    id = 'create_disk'
    name = _("create disk")
    description = _("Create and attach empty disk to the virtual machine.")
    required_perms = ('storage.create_empty_disk', )
    accept_states = ('STOPPED', 'PENDING', 'RUNNING')

    def _operation(self, user, size, activity, name=None):
        from storage.models import Disk

        if not name:
            name = "new disk"
        disk = Disk.create(size=size, name=name, type="qcow2-norm")
        disk.full_clean()
        devnums = list(ascii_lowercase)
        for d in self.instance.disks.all():
            devnums.remove(d.dev_num)
        disk.dev_num = devnums.pop(0)
        disk.save()
        self.instance.disks.add(disk)

        if self.instance.is_running:
            with activity.sub_activity(
                'deploying_disk',
                readable_name=ugettext_noop("deploying disk")
            ):
                disk.deploy()
            self.instance._attach_disk(parent_activity=activity, disk=disk)

    def get_activity_name(self, kwargs):
        return create_readable(
            ugettext_noop("create disk %(name)s (%(size)s)"),
            size=filesizeformat(kwargs['size']), name=kwargs['name'])


@register_operation
class ResizeDiskOperation(RemoteInstanceOperation):

    id = 'resize_disk'
    name = _("resize disk")
    description = _("Resize the virtual disk image. "
                    "Size must be greater value than the actual size.")
    required_perms = ('storage.resize_disk', )
    accept_states = ('RUNNING', )
    async_queue = "localhost.man.slow"
    remote_queue = ('vm', 'slow')
    task = vm_tasks.resize_disk

    def _get_remote_args(self, disk, size, **kwargs):
        return (super(ResizeDiskOperation, self)
                ._get_remote_args(**kwargs) + [disk.path, size])

    def get_activity_name(self, kwargs):
        return create_readable(
            ugettext_noop("resize disk %(name)s to %(size)s"),
            size=filesizeformat(kwargs['size']), name=kwargs['disk'].name)

    def _operation(self, disk, size):
        if not disk.is_resizable:
            raise HumanReadableException.create(ugettext_noop(
                'Disk type "%(type)s" is not resizable.'), type=disk.type)
        super(ResizeDiskOperation, self)._operation(disk=disk, size=size)
        disk.size = size
        disk.save()


@register_operation
class DownloadDiskOperation(InstanceOperation):
    id = 'download_disk'
    name = _("download disk")
    description = _("Download and attach disk image (ISO file) for the "
                    "virtual machine. Most operating systems do not detect a "
                    "new optical drive, so you may have to reboot the "
                    "machine.")
    abortable = True
    has_percentage = True
    required_perms = ('storage.download_disk', )
    accept_states = ('STOPPED', 'PENDING', 'RUNNING')
    async_queue = "localhost.man.slow"

    def _operation(self, user, url, task, activity, name=None):
        from storage.models import Disk

        disk = Disk.download(url=url, name=name, task=task)
        devnums = list(ascii_lowercase)
        for d in self.instance.disks.all():
            devnums.remove(d.dev_num)
        disk.dev_num = devnums.pop(0)
        disk.full_clean()
        disk.save()
        self.instance.disks.add(disk)
        activity.readable_name = create_readable(
            ugettext_noop("download %(name)s"), name=disk.name)

        activity.result = create_readable(ugettext_noop(
            "Downloading %(url)s is finished. The file md5sum "
            "is: '%(checksum)s'."),
            url=url, checksum=disk.checksum)
        # TODO iso (cd) hot-plug is not supported by kvm/guests
        if self.instance.is_running and disk.type not in ["iso"]:
            self.instance._attach_disk(parent_activity=activity, disk=disk)


@register_operation
class DeployOperation(InstanceOperation):
    id = 'deploy'
    name = _("deploy")
    description = _("Deploy and start the virtual machine (including storage "
                    "and network configuration).")
    required_perms = ()
    deny_states = ('SUSPENDED', 'RUNNING')
    resultant_state = 'RUNNING'

    def is_preferred(self):
        return self.instance.status in (self.instance.STATUS.STOPPED,
                                        self.instance.STATUS.PENDING,
                                        self.instance.STATUS.ERROR)

    def on_abort(self, activity, error):
        activity.resultant_state = 'STOPPED'

    def on_commit(self, activity):
        activity.resultant_state = 'RUNNING'
        activity.result = create_readable(
            ugettext_noop("virtual machine successfully "
                          "deployed to node: %(node)s"),
            node=self.instance.node)

    def _operation(self, activity, node=None):
        # Allocate VNC port and host node
        self.instance.allocate_vnc_port()
        if node is not None:
            self.instance.node = node
            self.instance.save()
        else:
            self.instance.allocate_node()

        # Deploy virtual images
        try:
            self.instance._deploy_disks(parent_activity=activity)
        except:
            self.instance.yield_node()
            self.instance.yield_vnc_port()
            raise

        # Deploy VM on remote machine
        if self.instance.state not in ['PAUSED']:
            self.instance._deploy_vm(parent_activity=activity)

        # Establish network connection (vmdriver)
        with activity.sub_activity(
            'deploying_net', readable_name=ugettext_noop(
                "deploy network")):
            self.instance.deploy_net()

        try:
            self.instance.renew(parent_activity=activity)
        except:
            pass

        self.instance._resume_vm(parent_activity=activity)

        if self.instance.has_agent:
            activity.sub_activity('os_boot', readable_name=ugettext_noop(
                "wait operating system loading"), interruptible=True)

    @register_operation
    class DeployVmOperation(SubOperationMixin, RemoteInstanceOperation):
        id = "_deploy_vm"
        name = _("deploy vm")
        description = _("Deploy virtual machine.")
        remote_queue = ("vm", "slow")
        task = vm_tasks.deploy

        def _get_remote_args(self, **kwargs):
            return [self.instance.get_vm_desc()]
            # intentionally not calling super

        def get_activity_name(self, kwargs):
            return create_readable(ugettext_noop("deploy virtual machine"),
                                   ugettext_noop("deploy vm to %(node)s"),
                                   node=self.instance.node)

    @register_operation
    class DeployDisksOperation(SubOperationMixin, InstanceOperation):
        id = "_deploy_disks"
        name = _("deploy disks")
        description = _("Deploy all associated disks.")

        def _operation(self):
            devnums = list(ascii_lowercase)  # a-z
            for disk in self.instance.disks.all():
                # assign device numbers
                if disk.dev_num in devnums:
                    devnums.remove(disk.dev_num)
                else:
                    disk.dev_num = devnums.pop(0)
                    disk.save()
                # deploy disk
                disk.deploy()

    @register_operation
    class ResumeVmOperation(SubOperationMixin, RemoteInstanceOperation):
        id = "_resume_vm"
        name = _("boot virtual machine")
        remote_queue = ("vm", "slow")
        task = vm_tasks.resume


@register_operation
class DestroyOperation(InstanceOperation):
    id = 'destroy'
    name = _("destroy")
    description = _("Permanently destroy virtual machine, its network "
                    "settings and disks.")
    required_perms = ()
    resultant_state = 'DESTROYED'

    def on_abort(self, activity, error):
        activity.resultant_state = None

    def _operation(self, activity, system):
        # Destroy networks
        with activity.sub_activity(
                'destroying_net',
                readable_name=ugettext_noop("destroy network")):
            if self.instance.node:
                self.instance.shutdown_net()
            self.instance.destroy_net()

        if self.instance.node:
            self.instance._delete_vm(parent_activity=activity)

        # Destroy disks
        with activity.sub_activity(
                'destroying_disks',
                readable_name=ugettext_noop("destroy disks")):
            self.instance.destroy_disks()

        # Delete mem. dump if exists
        try:
            self.instance._delete_mem_dump(parent_activity=activity)
        except:
            pass

        # Clear node and VNC port association
        self.instance.yield_node()
        self.instance.yield_vnc_port()

        self.instance.destroyed_at = timezone.now()
        self.instance.save()

    @register_operation
    class DeleteVmOperation(SubOperationMixin, RemoteInstanceOperation):
        id = "_delete_vm"
        name = _("destroy virtual machine")
        task = vm_tasks.destroy
        # if e.libvirtError and "Domain not found" in str(e):

    @register_operation
    class DeleteMemDumpOperation(RemoteOperationMixin, SubOperationMixin,
                                 InstanceOperation):
        id = "_delete_mem_dump"
        name = _("removing memory dump")
        task = storage_tasks.delete_dump

        def _get_remote_queue(self):
            return self.instance.mem_dump['datastore'].get_remote_queue_name(
                "storage", "fast")

        def _get_remote_args(self, **kwargs):
            return [self.instance.mem_dump['path']]


@register_operation
class MigrateOperation(RemoteInstanceOperation):
    id = 'migrate'
    name = _("migrate")
    description = _("Move a running virtual machine to an other worker node "
                    "keeping its full state.")
    required_perms = ()
    superuser_required = True
    accept_states = ('RUNNING', )
    async_queue = "localhost.man.slow"
    task = vm_tasks.migrate
    remote_queue = ("vm", "slow")
    remote_timeout = 1000

    def _get_remote_args(self, to_node, live_migration, **kwargs):
        return (super(MigrateOperation, self)._get_remote_args(**kwargs) +
                [to_node.host.hostname, live_migration])

    def rollback(self, activity):
        with activity.sub_activity(
            'rollback_net', readable_name=ugettext_noop(
                "redeploy network (rollback)")):
            self.instance.deploy_net()

    def _operation(self, activity, to_node=None, live_migration=True):
        if not to_node:
            with activity.sub_activity('scheduling',
                                       readable_name=ugettext_noop(
                                           "schedule")) as sa:
                to_node = self.instance.select_node()
                sa.result = to_node

        try:
            with activity.sub_activity(
                'migrate_vm', readable_name=create_readable(
                    ugettext_noop("migrate to %(node)s"), node=to_node)):
                super(MigrateOperation, self)._operation(
                    to_node=to_node, live_migration=live_migration)
        except Exception as e:
            if hasattr(e, 'libvirtError'):
                self.rollback(activity)
            raise

        # Shutdown networks
        with activity.sub_activity(
            'shutdown_net', readable_name=ugettext_noop(
                "shutdown network")):
            self.instance.shutdown_net()

        # Refresh node information
        self.instance.node = to_node
        self.instance.save()

        # Estabilish network connection (vmdriver)
        with activity.sub_activity(
            'deploying_net', readable_name=ugettext_noop(
                "deploy network")):
            self.instance.deploy_net()


@register_operation
class RebootOperation(RemoteInstanceOperation):
    id = 'reboot'
    name = _("reboot")
    description = _("Warm reboot virtual machine by sending Ctrl+Alt+Del "
                    "signal to its console.")
    required_perms = ()
    accept_states = ('RUNNING', )
    task = vm_tasks.reboot

    def _operation(self, activity):
        super(RebootOperation, self)._operation()
        if self.instance.has_agent:
            activity.sub_activity('os_boot', readable_name=ugettext_noop(
                "wait operating system loading"), interruptible=True)


@register_operation
class RemoveInterfaceOperation(InstanceOperation):
    id = 'remove_interface'
    name = _("remove interface")
    description = _("Remove the specified network interface and erase IP "
                    "address allocations, related firewall rules and "
                    "hostnames.")
    required_perms = ()
    accept_states = ('STOPPED', 'PENDING', 'RUNNING')

    def _operation(self, activity, user, system, interface):
        if self.instance.is_running:
            self.instance._detach_network(interface=interface,
                                          parent_activity=activity)
            interface.shutdown()

        interface.destroy()
        interface.delete()

    def get_activity_name(self, kwargs):
        return create_readable(ugettext_noop("remove %(vlan)s interface"),
                               vlan=kwargs['interface'].vlan)


@register_operation
class RemovePortOperation(InstanceOperation):
    id = 'remove_port'
    name = _("close port")
    description = _("Close the specified port.")
    concurrency_check = False
    acl_level = "operator"
    required_perms = ('vm.config_ports', )

    def _operation(self, activity, rule):
        interface = rule.host.interface_set.get()
        if interface.instance != self.instance:
            raise SuspiciousOperation()
        activity.readable_name = create_readable(
            ugettext_noop("close %(proto)s/%(port)d on %(host)s"),
            proto=rule.proto, port=rule.dport, host=rule.host)
        rule.delete()


@register_operation
class AddPortOperation(InstanceOperation):
    id = 'add_port'
    name = _("open port")
    description = _("Open the specified port.")
    concurrency_check = False
    acl_level = "operator"
    required_perms = ('vm.config_ports', )

    def _operation(self, activity, host, proto, port):
        if host.interface_set.get().instance != self.instance:
            raise SuspiciousOperation()
        host.add_port(proto, private=port)
        activity.readable_name = create_readable(
            ugettext_noop("open %(proto)s/%(port)d on %(host)s"),
            proto=proto, port=port, host=host)


@register_operation
class RemoveDiskOperation(InstanceOperation):
    id = 'remove_disk'
    name = _("remove disk")
    description = _("Remove the specified disk from the virtual machine, and "
                    "destroy the data.")
    required_perms = ()
    accept_states = ('STOPPED', 'PENDING', 'RUNNING')

    def _operation(self, activity, user, system, disk):
        if self.instance.is_running and disk.type not in ["iso"]:
            self.instance._detach_disk(disk=disk, parent_activity=activity)
        with activity.sub_activity(
            'destroy_disk',
            readable_name=ugettext_noop('destroy disk')
        ):
            disk.destroy()
            return self.instance.disks.remove(disk)

    def get_activity_name(self, kwargs):
        return create_readable(ugettext_noop('remove disk %(name)s'),
                               name=kwargs["disk"].name)


@register_operation
class ResetOperation(RemoteInstanceOperation):
    id = 'reset'
    name = _("reset")
    description = _("Cold reboot virtual machine (power cycle).")
    required_perms = ()
    accept_states = ('RUNNING', )
    task = vm_tasks.reset

    def _operation(self, activity):
        super(ResetOperation, self)._operation()
        if self.instance.has_agent:
            activity.sub_activity('os_boot', readable_name=ugettext_noop(
                "wait operating system loading"), interruptible=True)


@register_operation
class SaveAsTemplateOperation(InstanceOperation):
    id = 'save_as_template'
    name = _("save as template")
    description = _("Save virtual machine as a template so they can be shared "
                    "with users and groups.  Anyone who has access to a "
                    "template (and to the networks it uses) will be able to "
                    "start an instance of it.")
    has_percentage = True
    abortable = True
    required_perms = ('vm.create_template', )
    accept_states = ('RUNNING', 'STOPPED')
    async_queue = "localhost.man.slow"

    def is_preferred(self):
        return (self.instance.is_base and
                self.instance.status == self.instance.STATUS.RUNNING)

    @staticmethod
    def _rename(name):
        m = search(r" v(\d+)$", name)
        if m:
            v = int(m.group(1)) + 1
            name = search(r"^(.*) v(\d+)$", name).group(1)
        else:
            v = 1
        return "%s v%d" % (name, v)

    def on_abort(self, activity, error):
        if hasattr(self, 'disks'):
            for disk in self.disks:
                disk.destroy()

    def _operation(self, activity, user, system, name=None,
                   with_shutdown=True, clone=False, task=None, **kwargs):
        try:
            self.instance._cleanup(parent_activity=activity, user=user)
        except:
            pass

        if with_shutdown:
            try:
                self.instance.shutdown(parent_activity=activity,
                                       user=user, task=task)
            except Instance.WrongStateError:
                pass

        # prepare parameters
        params = {
            'access_method': self.instance.access_method,
            'arch': self.instance.arch,
            'boot_menu': self.instance.boot_menu,
            'description': self.instance.description,
            'lease': self.instance.lease,  # Can be problem in new VM
            'max_ram_size': self.instance.max_ram_size,
            'name': name or self._rename(self.instance.name),
            'num_cores': self.instance.num_cores,
            'owner': user,
            'parent': self.instance.template or None,  # Can be problem
            'priority': self.instance.priority,
            'ram_size': self.instance.ram_size,
            'raw_data': self.instance.raw_data,
            'system': self.instance.system,
        }
        params.update(kwargs)
        params.pop("parent_activity", None)

        from storage.models import Disk

        def __try_save_disk(disk):
            try:
                return disk.save_as(task)
            except Disk.WrongDiskTypeError:
                return disk

        self.disks = []
        for disk in self.instance.disks.all():
            with activity.sub_activity(
                'saving_disk',
                readable_name=create_readable(
                    ugettext_noop("saving disk %(name)s"),
                    name=disk.name)
            ):
                self.disks.append(__try_save_disk(disk))

        # create template and do additional setup
        tmpl = InstanceTemplate(**params)
        tmpl.full_clean()  # Avoiding database errors.
        tmpl.save()
        # Copy traits from the VM instance
        tmpl.req_traits.add(*self.instance.req_traits.all())
        if clone:
            tmpl.clone_acl(self.instance.template)
            # Add permission for the original owner of the template
            tmpl.set_level(self.instance.template.owner, 'owner')
            tmpl.set_level(user, 'owner')
        try:
            tmpl.disks.add(*self.disks)
            # create interface templates
            for i in self.instance.interface_set.all():
                i.save_as_template(tmpl)
        except:
            tmpl.delete()
            raise
        else:
            return create_readable(
                ugettext_noop("New template: %(template)s"),
                template=reverse('dashboard.views.template-detail',
                                 kwargs={'pk': tmpl.pk}))


@register_operation
class ShutdownOperation(AbortableRemoteOperationMixin,
                        RemoteInstanceOperation):
    id = 'shutdown'
    name = _("shutdown")
    description = _("Try to halt virtual machine by a standard ACPI signal, "
                    "allowing the operating system to keep a consistent "
                    "state. The operation will fail if the machine does not "
                    "turn itself off in a period.")
    abortable = True
    required_perms = ()
    accept_states = ('RUNNING', )
    resultant_state = 'STOPPED'
    task = vm_tasks.shutdown
    remote_queue = ("vm", "slow")
    remote_timeout = 180

    def _operation(self, task):
        super(ShutdownOperation, self)._operation(task=task)
        self.instance.yield_node()

    def on_abort(self, activity, error):
        if isinstance(error, TimeLimitExceeded):
            activity.result = humanize_exception(ugettext_noop(
                "The virtual machine did not switch off in the provided time "
                "limit. Most of the time this is caused by incorrect ACPI "
                "settings. You can also try to power off the machine from the "
                "operating system manually."), error)
            activity.resultant_state = None
        else:
            super(ShutdownOperation, self).on_abort(activity, error)


@register_operation
class ShutOffOperation(InstanceOperation):
    id = 'shut_off'
    name = _("shut off")
    description = _("Forcibly halt a virtual machine without notifying the "
                    "operating system. This operation will even work in cases "
                    "when shutdown does not, but the operating system and the "
                    "file systems are likely to be in an inconsistent state,  "
                    "so data loss is also possible. The effect of this "
                    "operation is the same as interrupting the power supply "
                    "of a physical machine.")
    required_perms = ()
    accept_states = ('RUNNING', 'PAUSED')
    resultant_state = 'STOPPED'

    def _operation(self, activity):
        # Shutdown networks
        with activity.sub_activity('shutdown_net',
                                   readable_name=ugettext_noop(
                                       "shutdown network")):
            self.instance.shutdown_net()

        self.instance._delete_vm(parent_activity=activity)
        self.instance.yield_node()


@register_operation
class SleepOperation(InstanceOperation):
    id = 'sleep'
    name = _("sleep")
    description = _("Suspend virtual machine. This means the machine is "
                    "stopped and its memory is saved to disk, so if the "
                    "machine is waked up, all the applications will keep "
                    "running. Most of the applications will be able to "
                    "continue even after a long suspension, but those which "
                    "need a continous network connection may fail when "
                    "resumed. In the meantime, the machine will only use "
                    "storage resources, and keep network resources allocated.")
    required_perms = ()
    accept_states = ('RUNNING', )
    resultant_state = 'SUSPENDED'
    async_queue = "localhost.man.slow"

    def is_preferred(self):
        return (not self.instance.is_base and
                self.instance.status == self.instance.STATUS.RUNNING)

    def on_abort(self, activity, error):
        if isinstance(error, TimeLimitExceeded):
            activity.resultant_state = None
        else:
            activity.resultant_state = 'ERROR'

    def _operation(self, activity, system):
        with activity.sub_activity('shutdown_net',
                                   readable_name=ugettext_noop(
                                       "shutdown network")):
            self.instance.shutdown_net()
        self.instance._suspend_vm(parent_activity=activity)
        self.instance.yield_node()

    @register_operation
    class SuspendVmOperation(SubOperationMixin, RemoteInstanceOperation):
        id = "_suspend_vm"
        name = _("suspend virtual machine")
        task = vm_tasks.sleep
        remote_queue = ("vm", "slow")
        remote_timeout = 1000

        def _get_remote_args(self, **kwargs):
            return (super(SleepOperation.SuspendVmOperation, self)
                    ._get_remote_args(**kwargs) +
                    [self.instance.mem_dump['path']])


@register_operation
class WakeUpOperation(InstanceOperation):
    id = 'wake_up'
    name = _("wake up")
    description = _("Wake up sleeping (suspended) virtual machine. This will "
                    "load the saved memory of the system and start the "
                    "virtual machine from this state.")
    required_perms = ()
    accept_states = ('SUSPENDED', )
    resultant_state = 'RUNNING'
    async_queue = "localhost.man.slow"

    def is_preferred(self):
        return self.instance.status == self.instance.STATUS.SUSPENDED

    def on_abort(self, activity, error):
        if isinstance(error, SchedulerError):
            activity.resultant_state = None
        else:
            activity.resultant_state = 'ERROR'

    def _operation(self, activity):
        # Schedule vm
        self.instance.allocate_vnc_port()
        self.instance.allocate_node()

        # Resume vm
        self.instance._wake_up_vm(parent_activity=activity)

        # Estabilish network connection (vmdriver)
        with activity.sub_activity(
            'deploying_net', readable_name=ugettext_noop(
                "deploy network")):
            self.instance.deploy_net()

        try:
            self.instance.renew(parent_activity=activity)
        except:
            pass

    @register_operation
    class WakeUpVmOperation(SubOperationMixin, RemoteInstanceOperation):
        id = "_wake_up_vm"
        name = _("resume virtual machine")
        task = vm_tasks.wake_up
        remote_queue = ("vm", "slow")
        remote_timeout = 1000

        def _get_remote_args(self, **kwargs):
            return (super(WakeUpOperation.WakeUpVmOperation, self)
                    ._get_remote_args(**kwargs) +
                    [self.instance.mem_dump['path']])


@register_operation
class RenewOperation(InstanceOperation):
    id = 'renew'
    name = _("renew")
    description = _("Virtual machines are suspended and destroyed after they "
                    "expire. This operation renews expiration times according "
                    "to the lease type. If the machine is close to the "
                    "expiration, its owner will be notified.")
    acl_level = "operator"
    required_perms = ()
    concurrency_check = False

    def set_time_of_suspend(self, activity, suspend, force):
        with activity.sub_activity(
            'renew_suspend', concurrency_check=False,
                readable_name=ugettext_noop('set time of suspend')):
            if (not force and suspend and self.instance.time_of_suspend and
                    suspend < self.instance.time_of_suspend):
                raise HumanReadableException.create(ugettext_noop(
                    "Renewing the machine with the selected lease would "
                    "result in its suspension time get earlier than before."))
            self.instance.time_of_suspend = suspend

    def set_time_of_delete(self, activity, delete, force):
        with activity.sub_activity(
            'renew_delete', concurrency_check=False,
                readable_name=ugettext_noop('set time of delete')):
            if (not force and delete and self.instance.time_of_delete and
                    delete < self.instance.time_of_delete):
                raise HumanReadableException.create(ugettext_noop(
                    "Renewing the machine with the selected lease would "
                    "result in its delete time get earlier than before."))
            self.instance.time_of_delete = delete

    def _operation(self, activity, lease=None, force=False, save=False):
        suspend, delete = self.instance.get_renew_times(lease)
        try:
            self.set_time_of_suspend(activity, suspend, force)
        except HumanReadableException:
            pass
        try:
            self.set_time_of_delete(activity, delete, force)
        except HumanReadableException:
            pass

        if save:
            self.instance.lease = lease

        self.instance.save()

        return create_readable(ugettext_noop(
            "Renewed to suspend at %(suspend)s and destroy at %(delete)s."),
            suspend=self.instance.time_of_suspend,
            delete=self.instance.time_of_suspend)


@register_operation
class ChangeStateOperation(InstanceOperation):
    id = 'emergency_change_state'
    name = _("emergency state change")
    description = _("Change the virtual machine state to NOSTATE. This "
                    "should only be used if manual intervention was needed in "
                    "the virtualization layer, and the machine has to be "
                    "redeployed without losing its storage and network "
                    "resources.")
    acl_level = "owner"
    required_perms = ('vm.emergency_change_state', )
    concurrency_check = False

    def _operation(self, user, activity, new_state="NOSTATE", interrupt=False,
                   reset_node=False):
        activity.resultant_state = new_state
        if interrupt:
            msg_txt = ugettext_noop("Activity is forcibly interrupted.")
            message = create_readable(msg_txt, msg_txt)
            for i in InstanceActivity.objects.filter(
                    finished__isnull=True, instance=self.instance):
                i.finish(False, result=message)
                logger.error('Forced finishing activity %s', i)

        if reset_node:
            self.instance.node = None
            self.instance.save()


@register_operation
class RedeployOperation(InstanceOperation):
    id = 'redeploy'
    name = _("redeploy")
    description = _("Change the virtual machine state to NOSTATE "
                    "and redeploy the VM. This operation allows starting "
                    "machines formerly running on a failed node.")
    acl_level = "owner"
    required_perms = ('vm.redeploy', )
    concurrency_check = False

    def _operation(self, user, activity, with_emergency_change_state=True):
        if with_emergency_change_state:
            ChangeStateOperation(self.instance).call(
                parent_activity=activity, user=user,
                new_state='NOSTATE', interrupt=False, reset_node=True)
        else:
            ShutOffOperation(self.instance).call(
                parent_activity=activity, user=user)

        self.instance._update_status()

        DeployOperation(self.instance).call(
            parent_activity=activity, user=user)


class NodeOperation(Operation):
    async_operation = abortable_async_node_operation
    host_cls = Node
    online_required = True
    superuser_required = True

    def __init__(self, node):
        super(NodeOperation, self).__init__(subject=node)
        self.node = node

    def check_precond(self):
        super(NodeOperation, self).check_precond()
        if self.online_required and not self.node.online:
            raise humanize_exception(ugettext_noop(
                "You cannot call this operation on an offline node."),
                Exception())

    def create_activity(self, parent, user, kwargs):
        name = self.get_activity_name(kwargs)
        if parent:
            if parent.node != self.node:
                raise ValueError("The node associated with the specified "
                                 "parent activity does not match the node "
                                 "bound to the operation.")
            if parent.user != user:
                raise ValueError("The user associated with the specified "
                                 "parent activity does not match the user "
                                 "provided as parameter.")

            return parent.create_sub(
                code_suffix=self.get_activity_code_suffix(),
                readable_name=name)
        else:
            return NodeActivity.create(
                code_suffix=self.get_activity_code_suffix(), node=self.node,
                user=user, readable_name=name)


@register_operation
class ResetNodeOperation(NodeOperation):
    id = 'reset'
    name = _("reset")
    description = _("Disable missing node and redeploy all instances "
                    "on other ones.")
    required_perms = ()
    online_required = False
    async_queue = "localhost.man.slow"

    def check_precond(self):
        super(ResetNodeOperation, self).check_precond()
        if not self.node.enabled or self.node.online:
            raise humanize_exception(ugettext_noop(
                "You cannot reset a disabled or online node."), Exception())

    def _operation(self, activity, user):
        for i in self.node.instance_set.all():
            name = create_readable(ugettext_noop(
                "redeploy %(instance)s (%(pk)s)"), instance=i.name, pk=i.pk)
            with activity.sub_activity('migrate_instance_%d' % i.pk,
                                       readable_name=name):
                i.redeploy(user=user)

        self.node.enabled = False
        self.node.schedule_enabled = False
        self.node.save()


@register_operation
class FlushOperation(NodeOperation):
    id = 'flush'
    name = _("flush")
    description = _("Passivate node and move all instances to other ones.")
    required_perms = ()
    async_queue = "localhost.man.slow"

    def _operation(self, activity, user):
        if self.node.schedule_enabled:
            PassivateOperation(self.node).call(parent_activity=activity,
                                               user=user)
        for i in self.node.instance_set.all():
            name = create_readable(ugettext_noop(
                "migrate %(instance)s (%(pk)s)"), instance=i.name, pk=i.pk)
            with activity.sub_activity('migrate_instance_%d' % i.pk,
                                       readable_name=name):
                i.migrate(user=user)


@register_operation
class ActivateOperation(NodeOperation):
    id = 'activate'
    name = _("activate")
    description = _("Make node active, i.e. scheduler is allowed to deploy "
                    "virtual machines to it.")
    required_perms = ()

    def check_precond(self):
        super(ActivateOperation, self).check_precond()
        if self.node.enabled and self.node.schedule_enabled:
            raise humanize_exception(ugettext_noop(
                "You cannot activate an active node."), Exception())

    def _operation(self):
        self.node.enabled = True
        self.node.schedule_enabled = True
        self.node.get_info(invalidate_cache=True)
        self.node.save()


@register_operation
class PassivateOperation(NodeOperation):
    id = 'passivate'
    name = _("passivate")
    description = _("Make node passive, i.e. scheduler is denied to deploy "
                    "virtual machines to it, but remaining instances and "
                    "the ones manually migrated will continue running.")
    required_perms = ()

    def check_precond(self):
        if self.node.enabled and not self.node.schedule_enabled:
            raise humanize_exception(ugettext_noop(
                "You cannot passivate a passive node."), Exception())
        super(PassivateOperation, self).check_precond()

    def _operation(self):
        self.node.enabled = True
        self.node.schedule_enabled = False
        self.node.get_info(invalidate_cache=True)
        self.node.save()


@register_operation
class DisableOperation(NodeOperation):
    id = 'disable'
    name = _("disable")
    description = _("Disable node.")
    required_perms = ()
    online_required = False

    def check_precond(self):
        if not self.node.enabled:
            raise humanize_exception(ugettext_noop(
                "You cannot disable a disabled node."), Exception())
        if self.node.instance_set.exists():
            raise humanize_exception(ugettext_noop(
                "You cannot disable a node which is hosting instances."),
                Exception())
        super(DisableOperation, self).check_precond()

    def _operation(self):
        self.node.enabled = False
        self.node.schedule_enabled = False
        self.node.save()


@register_operation
class UpdateNodeOperation(NodeOperation):
    id = 'update_node'
    name = _("update node")
    description = _("Upgrade or install node software (vmdriver, agentdriver, "
                    "monitor-client) with Salt.")
    required_perms = ()
    online_required = False
    async_queue = "localhost.man.slow"

    def minion_cmd(self, module, params, timeout=3600):
        # see https://git.ik.bme.hu/circle/cloud/issues/377
        from salt.client import LocalClient
        name = self.node.host.hostname
        client = LocalClient()
        data = client.cmd(
            name, module, params, timeout=timeout)

        try:
            data = data[name]
        except KeyError:
            raise HumanReadableException.create(ugettext_noop(
                "No minions matched the target (%(target)s). "
                "Data: (%(data)s)"), target=name, data=data)

        if not isinstance(data, dict):
            raise HumanReadableException.create(ugettext_noop(
                "Unhandled exception: %(msg)s"), msg=unicode(data))

        return data

    def _operation(self, activity):
        with activity.sub_activity(
                'upgrade_packages',
                readable_name=ugettext_noop('upgrade packages')) as sa:
            data = self.minion_cmd('pkg.upgrade', [])
            if not data.get('result'):
                raise HumanReadableException.create(ugettext_noop(
                    "Unhandled exception: %(msg)s"), msg=unicode(data))

            # data = {'vim': {'new': '1.2.7', 'old': '1.3.7'}}
            data = [v for v in data.values() if isinstance(v, dict)]
            upgraded = len([x for x in data
                            if x.get('old') and x.get('new')])
            installed = len([x for x in data
                             if not x.get('old') and x.get('new')])
            removed = len([x for x in data
                           if x.get('old') and not x.get('new')])
            sa.result = create_readable(ugettext_noop(
                "Upgraded: %(upgraded)s, Installed: %(installed)s, "
                "Removed: %(removed)s"), upgraded=upgraded,
                installed=installed, removed=removed)

        data = self.minion_cmd('state.sls', ['node'])
        failed = 0
        for k, v in data.iteritems():
            logger.debug('salt state %s %s', k, v)
            act_name = ': '.join(k.split('_|-')[:2])
            if not v["result"] or v["changes"]:
                act = activity.create_sub(
                    act_name[:70], readable_name=act_name)
                act.result = create_readable(ugettext_noop(
                    "Changes: %(changes)s Comment: %(comment)s"),
                    changes=v["changes"], comment=v["comment"])
                act.finish(v["result"])
                if not v["result"]:
                    failed += 1

        if failed:
            raise HumanReadableException.create(ugettext_noop(
                "Failed: %(failed)s"), failed=failed)


@register_operation
class ScreenshotOperation(RemoteInstanceOperation):
    id = 'screenshot'
    name = _("screenshot")
    description = _("Get a screenshot about the virtual machine's console. A "
                    "key will be pressed on the keyboard to stop "
                    "screensaver.")
    acl_level = "owner"
    required_perms = ()
    accept_states = ('RUNNING', )
    task = vm_tasks.screenshot


@register_operation
class RecoverOperation(InstanceOperation):
    id = 'recover'
    name = _("recover")
    description = _("Try to recover virtual machine disks from destroyed "
                    "state. Network resources (allocations) are already lost, "
                    "so you will have to manually add interfaces afterwards.")
    acl_level = "owner"
    required_perms = ('vm.recover', )
    accept_states = ('DESTROYED', )
    resultant_state = 'PENDING'

    def check_precond(self):
        try:
            super(RecoverOperation, self).check_precond()
        except Instance.InstanceDestroyedError:
            pass

    def _operation(self, user, activity):
        with activity.sub_activity(
            'recover_instance',
                readable_name=ugettext_noop("recover instance")):
            self.instance.destroyed_at = None
            for disk in self.instance.disks.all():
                disk.destroyed = None
                disk.restore()
                disk.save()
            self.instance.status = 'PENDING'
            self.instance.save()

        try:
            self.instance.renew(parent_activity=activity)
        except:
            pass

        if self.instance.template:
            for net in self.instance.template.interface_set.all():
                self.instance.add_interface(
                    parent_activity=activity, user=user, vlan=net.vlan)


@register_operation
class ResourcesOperation(InstanceOperation):
    id = 'resources_change'
    name = _("resources change")
    description = _("Change resources of a stopped virtual machine.")
    acl_level = "owner"
    required_perms = ('vm.change_resources', )
    accept_states = ('STOPPED', 'PENDING', 'RUNNING')

    def _operation(self, user, activity,
                   num_cores, ram_size, max_ram_size, priority,
                   with_shutdown=False, task=None):
        if self.instance.status == 'RUNNING' and not with_shutdown:
            raise Instance.WrongStateError(self.instance)

        try:
            self.instance.shutdown(parent_activity=activity, task=task)
        except Instance.WrongStateError:
            pass

        self.instance._update_status()

        self.instance.num_cores = num_cores
        self.instance.ram_size = ram_size
        self.instance.max_ram_size = max_ram_size
        self.instance.priority = priority

        self.instance.full_clean()
        self.instance.save()

        return create_readable(ugettext_noop(
            "Priority: %(priority)s, Num cores: %(num_cores)s, "
            "Ram size: %(ram_size)s"), priority=priority, num_cores=num_cores,
            ram_size=ram_size
        )


@register_operation
class ToggleBootMenuOperation(InstanceOperation):
    id = 'toggle_boot_menu'
    name = _("toggle boot menu")
    description = _("Turn on/off boot menu.")
    acl_level = "owner"
    required_perms = ('vm.toggle_boot_menu', )
    accept_states = ('STOPPED', )

    def _operation(self, user, activity, boot_menu):
        self.instance.boot_menu = boot_menu

        self.instance.full_clean()
        self.instance.save()

        return create_readable(ugettext_noop(
            "Boot menu toggled: %(boot_menu)s"),
            boot_menu="ON" if boot_menu else "OFF"
        )


@register_operation
class PasswordResetOperation(RemoteAgentOperation):
    id = 'password_reset'
    name = _("password reset")
    description = _("Generate and set a new login password on the virtual "
                    "machine. This operation requires the agent running. "
                    "Resetting the password is not warranted to allow you "
                    "logging in as other settings are possible to prevent "
                    "it.")
    acl_level = "owner"
    task = agent_tasks.change_password
    required_perms = ()

    def _get_remote_args(self, password, **kwrgs):
        return (super(PasswordResetOperation, self)._get_remote_args(**kwrgs) +
                [password])

    def _operation(self, password=None):
        if not password:
            password = pwgen()
        super(PasswordResetOperation, self)._operation(password=password)
        self.instance.pw = password
        self.instance.save()


@register_operation
class InstallKeysOperation(RemoteAgentOperation):
    id = 'install_keys'
    name = _("install SSH keys")
    description = _("Copy your public keys to the virtual machines. "
                    "Only works on UNIX-like operating systems.")
    acl_level = "user"
    task = agent_tasks.add_keys
    required_perms = ()

    def _get_remote_args(self, user, keys=None, **kwargs):
        if keys is None:
            keys = list(user.userkey_set.values_list('key', flat=True))
        return (super(InstallKeysOperation, self)._get_remote_args(**kwargs) +
                [keys])


@register_operation
class RemoveKeysOperation(RemoteAgentOperation):
    id = 'remove_keys'
    name = _("remove SSH keys")
    acl_level = "user"
    task = agent_tasks.del_keys
    required_perms = ()

    def _get_remote_args(self, user, keys, **kwargs):
        return (super(RemoveKeysOperation, self)._get_remote_args(**kwargs) +
                [keys])


@register_operation
class AgentStartedOperation(InstanceOperation):
    id = 'agent_started'
    name = _("agent")
    acl_level = "owner"
    required_perms = ()
    concurrency_check = False

    @classmethod
    def get_activity_code_suffix(cls):
        return 'agent'

    @property
    def initialized(self):
        return self.instance.activity_log.filter(
            activity_code='vm.Instance.agent._cleanup').exists()

    def measure_boot_time(self):
        if not self.instance.template:
            return

        deploy_time = InstanceActivity.objects.filter(
            instance=self.instance, activity_code="vm.Instance.deploy"
        ).latest("finished").finished

        total_boot_time = (timezone.now() - deploy_time).total_seconds()

        Client().send([
            "template.%(pk)d.boot_time %(val)f %(time)s" % {
                'pk': self.instance.template.pk,
                'val': total_boot_time,
                'time': time.time(),
            }
        ])

    def finish_agent_wait(self):
        for i in InstanceActivity.objects.filter(
                (Q(activity_code__endswith='.os_boot') |
                 Q(activity_code__endswith='.agent_wait')),
                instance=self.instance, finished__isnull=True):
            i.finish(True)

    def _operation(self, user, activity, old_version=None, agent_system=None):
        with activity.sub_activity('starting', concurrency_check=False,
                                   readable_name=ugettext_noop('starting')):
            pass

        self.finish_agent_wait()

        self.instance._change_ip(parent_activity=activity)
        self.instance._restart_networking(parent_activity=activity)

        new_version = settings.AGENT_VERSION
        if new_version and old_version and new_version != old_version:
            try:
                self.instance.update_agent(
                    parent_activity=activity, agent_system=agent_system)
            except TimeoutError:
                pass
            else:
                activity.sub_activity(
                    'agent_wait', readable_name=ugettext_noop(
                        "wait agent restarting"), interruptible=True)
                return  # agent is going to restart

        if not self.initialized:
            try:
                self.measure_boot_time()
            except:
                logger.exception('Unhandled error in measure_boot_time()')
            self.instance._cleanup(parent_activity=activity)
            self.instance.password_reset(
                parent_activity=activity, password=self.instance.pw)
            self.instance.install_keys(parent_activity=activity)
            self.instance._set_time(parent_activity=activity)
            self.instance._set_hostname(parent_activity=activity)

    @register_operation
    class CleanupOperation(SubOperationMixin, RemoteAgentOperation):
        id = '_cleanup'
        name = _("cleanup")
        task = agent_tasks.cleanup

    @register_operation
    class SetTimeOperation(SubOperationMixin, RemoteAgentOperation):
        id = '_set_time'
        name = _("set time")
        task = agent_tasks.set_time

        def _get_remote_args(self, **kwargs):
            cls = AgentStartedOperation.SetTimeOperation
            return (super(cls, self)._get_remote_args(**kwargs) +
                    [time.time()])

    @register_operation
    class SetHostnameOperation(SubOperationMixin, RemoteAgentOperation):
        id = '_set_hostname'
        name = _("set hostname")
        task = agent_tasks.set_hostname

        def _get_remote_args(self, **kwargs):
            cls = AgentStartedOperation.SetHostnameOperation
            return (super(cls, self)._get_remote_args(**kwargs) +
                    [self.instance.short_hostname])

    @register_operation
    class RestartNetworkingOperation(SubOperationMixin, RemoteAgentOperation):
        id = '_restart_networking'
        name = _("restart networking")
        task = agent_tasks.restart_networking

    @register_operation
    class ChangeIpOperation(SubOperationMixin, RemoteAgentOperation):
        id = '_change_ip'
        name = _("change ip")
        task = agent_tasks.change_ip

        def _get_remote_args(self, **kwargs):
            hosts = Host.objects.filter(interface__instance=self.instance)
            interfaces = {str(host.mac): host.get_network_config()
                          for host in hosts}
            cls = AgentStartedOperation.ChangeIpOperation
            return (super(cls, self)._get_remote_args(**kwargs) +
                    [interfaces, settings.FIREWALL_SETTINGS['rdns_ip']])


@register_operation
class UpdateAgentOperation(RemoteAgentOperation):
    id = 'update_agent'
    name = _("update agent")
    acl_level = "owner"
    required_perms = ()

    def get_activity_name(self, kwargs):
        return create_readable(
            ugettext_noop('update agent to %(version)s'),
            version=settings.AGENT_VERSION)

    @staticmethod
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

    @staticmethod
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

    def _operation(self, user, activity, agent_system):
        queue = self._get_remote_queue()
        instance = self.instance
        if agent_system == "Windows":
            executable = os.listdir(
                os.path.join(settings.AGENT_DIR, "agent-win"))[0]
            data = self.create_windows_tar()
        elif agent_system == "Linux":
            executable = ""
            data = self.create_linux_tar()
        else:
            # Legacy update method
            executable = ""
            return agent_tasks.update_legacy.apply_async(
                queue=queue,
                args=(instance.vm_name, self.create_linux_tar())
            ).get(timeout=60)

        checksum = md5(data).hexdigest()
        chunk_size = 1024 * 1024
        chunk_number = 0
        index = 0
        filename = settings.AGENT_VERSION + ".tar"
        while True:
            chunk = data[index:index+chunk_size]
            if chunk:
                agent_tasks.append.apply_async(
                    queue=queue,
                    args=(instance.vm_name, chunk,
                          filename, chunk_number)).get(timeout=60)
                index = index + chunk_size
                chunk_number = chunk_number + 1
            else:
                agent_tasks.update.apply_async(
                    queue=queue,
                    args=(instance.vm_name, filename, executable, checksum)
                ).get(timeout=60)
                break


@register_operation
class MountStoreOperation(EnsureAgentMixin, InstanceOperation):
    id = 'mount_store'
    name = _("mount store")
    description = _(
        "This operation attaches your personal file store. Other users who "
        "have access to this machine can see these files as well."
    )
    acl_level = "owner"
    required_perms = ()

    def check_auth(self, user):
        super(MountStoreOperation, self).check_auth(user)
        try:
            Store(user)
        except NoStoreException:
            raise PermissionDenied  # not show the button at all

    def _operation(self, user):
        inst = self.instance
        queue = self.instance.get_remote_queue_name("agent")
        host = urlsplit(settings.STORE_URL).hostname
        username = Store(user).username
        password = user.profile.smb_password
        agent_tasks.mount_store.apply_async(
            queue=queue, args=(inst.vm_name, host, username, password))


class AbstractDiskOperation(SubOperationMixin, RemoteInstanceOperation):
    required_perms = ()

    def _get_remote_args(self, disk, **kwargs):
        return (super(AbstractDiskOperation, self)._get_remote_args(**kwargs) +
                [disk.get_vmdisk_desc()])


@register_operation
class AttachDisk(AbstractDiskOperation):
    id = "_attach_disk"
    name = _("attach disk")
    task = vm_tasks.attach_disk


class DetachMixin(object):
    def _operation(self, activity, **kwargs):
        try:
            super(DetachMixin, self)._operation(**kwargs)
        except Exception as e:
            if hasattr(e, "libvirtError") and "not found" in unicode(e):
                activity.result = create_readable(
                    ugettext_noop("Resource was not found."),
                    ugettext_noop("Resource was not found. %(exception)s"),
                    exception=unicode(e))
            else:
                raise


@register_operation
class DetachDisk(DetachMixin, AbstractDiskOperation):
    id = "_detach_disk"
    name = _("detach disk")
    task = vm_tasks.detach_disk


class AbstractNetworkOperation(SubOperationMixin, RemoteInstanceOperation):
    required_perms = ()

    def _get_remote_args(self, interface, **kwargs):
        return (super(AbstractNetworkOperation, self)
                ._get_remote_args(**kwargs) + [interface.get_vmnetwork_desc()])


@register_operation
class AttachNetwork(AbstractNetworkOperation):
    id = "_attach_network"
    name = _("attach network")
    task = vm_tasks.attach_network


@register_operation
class DetachNetwork(DetachMixin, AbstractNetworkOperation):
    id = "_detach_network"
    name = _("detach network")
    task = vm_tasks.detach_network
