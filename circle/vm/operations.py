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
from logging import getLogger
from re import search
from string import ascii_lowercase
from urlparse import urlsplit

from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _, ugettext_noop
from django.conf import settings

from sizefield.utils import filesizeformat

from celery.exceptions import TimeLimitExceeded

from common.models import (
    create_readable, humanize_exception, HumanReadableException
)
from common.operations import Operation, register_operation
from manager.scheduler import SchedulerError
from .tasks.local_tasks import (
    abortable_async_instance_operation, abortable_async_node_operation,
)
from .models import (
    Instance, InstanceActivity, InstanceTemplate, Interface, Node,
    NodeActivity, pwgen
)
from .tasks import agent_tasks, local_agent_tasks

from dashboard.store_api import Store, NoStoreException

logger = getLogger(__name__)


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

            return parent.create_sub(code_suffix=self.activity_code_suffix,
                                     readable_name=name,
                                     resultant_state=self.resultant_state)
        else:
            return InstanceActivity.create(
                code_suffix=self.activity_code_suffix, instance=self.instance,
                readable_name=name, user=user,
                concurrency_check=self.concurrency_check,
                resultant_state=self.resultant_state)

    def is_preferred(self):
        """If this is the recommended op in the current state of the instance.
        """
        return False


class AddInterfaceOperation(InstanceOperation):
    activity_code_suffix = 'add_interface'
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
                with activity.sub_activity(
                    'attach_network',
                        readable_name=ugettext_noop("attach network")):
                    self.instance.attach_network(net)
            except Exception as e:
                if hasattr(e, 'libvirtError'):
                    self.rollback(net, activity)
                raise
            net.deploy()
            local_agent_tasks.send_networking_commands(self.instance, activity)

    def get_activity_name(self, kwargs):
        return create_readable(ugettext_noop("add %(vlan)s interface"),
                               vlan=kwargs['vlan'])


register_operation(AddInterfaceOperation)


class CreateDiskOperation(InstanceOperation):

    activity_code_suffix = 'create_disk'
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
            with activity.sub_activity(
                'attach_disk',
                readable_name=ugettext_noop("attach disk")
            ):
                self.instance.attach_disk(disk)

    def get_activity_name(self, kwargs):
        return create_readable(
            ugettext_noop("create disk %(name)s (%(size)s)"),
            size=filesizeformat(kwargs['size']), name=kwargs['name'])


register_operation(CreateDiskOperation)


class DownloadDiskOperation(InstanceOperation):
    activity_code_suffix = 'download_disk'
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
        activity.result = url
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

        # TODO iso (cd) hot-plug is not supported by kvm/guests
        if self.instance.is_running and disk.type not in ["iso"]:
            with activity.sub_activity(
                'attach_disk',
                readable_name=ugettext_noop("attach disk")
            ):
                self.instance.attach_disk(disk)

register_operation(DownloadDiskOperation)


class DeployOperation(InstanceOperation):
    activity_code_suffix = 'deploy'
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

    def _operation(self, activity, timeout=15):
        # Allocate VNC port and host node
        self.instance.allocate_vnc_port()
        self.instance.allocate_node()

        # Deploy virtual images
        with activity.sub_activity(
            'deploying_disks', readable_name=ugettext_noop(
                "deploy disks")):
            self.instance.deploy_disks()

        # Deploy VM on remote machine
        if self.instance.state not in ['PAUSED']:
            rn = create_readable(ugettext_noop("deploy virtual machine"),
                                 ugettext_noop("deploy vm to %(node)s"),
                                 node=self.instance.node)
            with activity.sub_activity(
                    'deploying_vm', readable_name=rn) as deploy_act:
                deploy_act.result = self.instance.deploy_vm(timeout=timeout)

        # Establish network connection (vmdriver)
        with activity.sub_activity(
            'deploying_net', readable_name=ugettext_noop(
                "deploy network")):
            self.instance.deploy_net()

        # Resume vm
        with activity.sub_activity(
            'booting', readable_name=ugettext_noop(
                "boot virtual machine")):
            self.instance.resume_vm(timeout=timeout)

        try:
            self.instance.renew(parent_activity=activity)
        except:
            pass


register_operation(DeployOperation)


class DestroyOperation(InstanceOperation):
    activity_code_suffix = 'destroy'
    id = 'destroy'
    name = _("destroy")
    description = _("Permanently destroy virtual machine, its network "
                    "settings and disks.")
    required_perms = ()
    resultant_state = 'DESTROYED'

    def _operation(self, activity):
        # Destroy networks
        with activity.sub_activity(
                'destroying_net',
                readable_name=ugettext_noop("destroy network")):
            if self.instance.node:
                self.instance.shutdown_net()
            self.instance.destroy_net()

        if self.instance.node:
            # Delete virtual machine
            with activity.sub_activity(
                    'destroying_vm',
                    readable_name=ugettext_noop("destroy virtual machine")):
                self.instance.delete_vm()

        # Destroy disks
        with activity.sub_activity(
                'destroying_disks',
                readable_name=ugettext_noop("destroy disks")):
            self.instance.destroy_disks()

        # Delete mem. dump if exists
        try:
            self.instance.delete_mem_dump()
        except:
            pass

        # Clear node and VNC port association
        self.instance.yield_node()
        self.instance.yield_vnc_port()

        self.instance.destroyed_at = timezone.now()
        self.instance.save()


register_operation(DestroyOperation)


class MigrateOperation(InstanceOperation):
    activity_code_suffix = 'migrate'
    id = 'migrate'
    name = _("migrate")
    description = _("Move virtual machine to an other worker node with a few "
                    "seconds of interruption (live migration).")
    required_perms = ()
    superuser_required = True
    accept_states = ('RUNNING', )
    async_queue = "localhost.man.slow"

    def rollback(self, activity):
        with activity.sub_activity(
            'rollback_net', readable_name=ugettext_noop(
                "redeploy network (rollback)")):
            self.instance.deploy_net()

    def _operation(self, activity, to_node=None, timeout=120):
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
                self.instance.migrate_vm(to_node=to_node, timeout=timeout)
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


register_operation(MigrateOperation)


class RebootOperation(InstanceOperation):
    activity_code_suffix = 'reboot'
    id = 'reboot'
    name = _("reboot")
    description = _("Warm reboot virtual machine by sending Ctrl+Alt+Del "
                    "signal to its console.")
    required_perms = ()
    accept_states = ('RUNNING', )

    def _operation(self, timeout=5):
        self.instance.reboot_vm(timeout=timeout)


register_operation(RebootOperation)


class RemoveInterfaceOperation(InstanceOperation):
    activity_code_suffix = 'remove_interface'
    id = 'remove_interface'
    name = _("remove interface")
    description = _("Remove the specified network interface and erase IP "
                    "address allocations, related firewall rules and "
                    "hostnames.")
    required_perms = ()
    accept_states = ('STOPPED', 'PENDING', 'RUNNING')

    def _operation(self, activity, user, system, interface):
        if self.instance.is_running:
            with activity.sub_activity(
                'detach_network',
                readable_name=ugettext_noop("detach network")
            ):
                self.instance.detach_network(interface)
            interface.shutdown()

        interface.destroy()
        interface.delete()

    def get_activity_name(self, kwargs):
        return create_readable(ugettext_noop("remove %(vlan)s interface"),
                               vlan=kwargs['interface'].vlan)


register_operation(RemoveInterfaceOperation)


class RemoveDiskOperation(InstanceOperation):
    activity_code_suffix = 'remove_disk'
    id = 'remove_disk'
    name = _("remove disk")
    description = _("Remove the specified disk from the virtual machine, and "
                    "destroy the data.")
    required_perms = ()
    accept_states = ('STOPPED', 'PENDING', 'RUNNING')

    def _operation(self, activity, user, system, disk):
        if self.instance.is_running and disk.type not in ["iso"]:
            with activity.sub_activity(
                'detach_disk',
                readable_name=ugettext_noop('detach disk')
            ):
                self.instance.detach_disk(disk)
        with activity.sub_activity(
            'destroy_disk',
            readable_name=ugettext_noop('destroy disk')
        ):
            return self.instance.disks.remove(disk)

    def get_activity_name(self, kwargs):
        return create_readable(ugettext_noop('remove disk %(name)s'),
                               name=kwargs["disk"].name)

register_operation(RemoveDiskOperation)


class ResetOperation(InstanceOperation):
    activity_code_suffix = 'reset'
    id = 'reset'
    name = _("reset")
    description = _("Cold reboot virtual machine (power cycle).")
    required_perms = ()
    accept_states = ('RUNNING', )

    def _operation(self, timeout=5):
        self.instance.reset_vm(timeout=timeout)

register_operation(ResetOperation)


class SaveAsTemplateOperation(InstanceOperation):
    activity_code_suffix = 'save_as_template'
    id = 'save_as_template'
    name = _("save as template")
    description = _("Save virtual machine as a template so they can be shared "
                    "with users and groups.  Anyone who has access to a "
                    "template (and to the networks it uses) will be able to "
                    "start an instance of it.")
    abortable = True
    required_perms = ('vm.create_template', )
    accept_states = ('RUNNING', 'PENDING', 'STOPPED')
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

    def _operation(self, activity, user, system, timeout=300, name=None,
                   with_shutdown=True, task=None, **kwargs):
        if with_shutdown:
            try:
                ShutdownOperation(self.instance).call(parent_activity=activity,
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
            'parent': self.instance.template,  # Can be problem
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
        try:
            tmpl.disks.add(*self.disks)
            # create interface templates
            for i in self.instance.interface_set.all():
                i.save_as_template(tmpl)
        except:
            tmpl.delete()
            raise
        else:
            return tmpl


register_operation(SaveAsTemplateOperation)


class ShutdownOperation(InstanceOperation):
    activity_code_suffix = 'shutdown'
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

    def _operation(self, task=None):
        self.instance.shutdown_vm(task=task)
        self.instance.yield_node()
        self.instance.yield_vnc_port()

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


register_operation(ShutdownOperation)


class ShutOffOperation(InstanceOperation):
    activity_code_suffix = 'shut_off'
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
    accept_states = ('RUNNING', )
    resultant_state = 'STOPPED'

    def _operation(self, activity):
        # Shutdown networks
        with activity.sub_activity('shutdown_net'):
            self.instance.shutdown_net()

        # Delete virtual machine
        with activity.sub_activity('delete_vm'):
            self.instance.delete_vm()

        # Clear node and VNC port association
        self.instance.yield_node()
        self.instance.yield_vnc_port()


register_operation(ShutOffOperation)


class SleepOperation(InstanceOperation):
    activity_code_suffix = 'sleep'
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

    def _operation(self, activity, timeout=240):
        # Destroy networks
        with activity.sub_activity('shutdown_net', readable_name=ugettext_noop(
                "shutdown network")):
            self.instance.shutdown_net()

        # Suspend vm
        with activity.sub_activity('suspending',
                                   readable_name=ugettext_noop(
                                       "suspend virtual machine")):
            self.instance.suspend_vm(timeout=timeout)

        self.instance.yield_node()
        # VNC port needs to be kept


register_operation(SleepOperation)


class WakeUpOperation(InstanceOperation):
    activity_code_suffix = 'wake_up'
    id = 'wake_up'
    name = _("wake up")
    description = _("Wake up sleeping (suspended) virtual machine. This will "
                    "load the saved memory of the system and start the "
                    "virtual machine from this state.")
    required_perms = ()
    accept_states = ('SUSPENDED', )
    resultant_state = 'RUNNING'

    def is_preferred(self):
        return self.instance.status == self.instance.STATUS.SUSPENDED

    def on_abort(self, activity, error):
        if isinstance(error, SchedulerError):
            activity.resultant_state = None
        else:
            activity.resultant_state = 'ERROR'

    def _operation(self, activity, timeout=60):
        # Schedule vm
        self.instance.allocate_vnc_port()
        self.instance.allocate_node()

        # Resume vm
        with activity.sub_activity(
            'resuming', readable_name=ugettext_noop(
                "resume virtual machine")):
            self.instance.wake_up_vm(timeout=timeout)

        # Estabilish network connection (vmdriver)
        with activity.sub_activity(
            'deploying_net', readable_name=ugettext_noop(
                "deploy network")):
            self.instance.deploy_net()

        try:
            self.instance.renew(parent_activity=activity)
        except:
            pass


register_operation(WakeUpOperation)


class RenewOperation(InstanceOperation):
    activity_code_suffix = 'renew'
    id = 'renew'
    name = _("renew")
    description = _("Virtual machines are suspended and destroyed after they "
                    "expire. This operation renews expiration times according "
                    "to the lease type. If the machine is close to the "
                    "expiration, its owner will be notified.")
    acl_level = "operator"
    required_perms = ()
    concurrency_check = False

    def _operation(self, activity, lease=None, force=False, save=False):
        suspend, delete = self.instance.get_renew_times(lease)
        if (not force and suspend and self.instance.time_of_suspend and
                suspend < self.instance.time_of_suspend):
            raise HumanReadableException.create(ugettext_noop(
                "Renewing the machine with the selected lease would result "
                "in its suspension time get earlier than before."))
        if (not force and delete and self.instance.time_of_delete and
                delete < self.instance.time_of_delete):
            raise HumanReadableException.create(ugettext_noop(
                "Renewing the machine with the selected lease would result "
                "in its delete time get earlier than before."))
        self.instance.time_of_suspend = suspend
        self.instance.time_of_delete = delete
        if save:
            self.instance.lease = lease
        self.instance.save()
        activity.result = create_readable(ugettext_noop(
            "Renewed to suspend at %(suspend)s and destroy at %(delete)s."),
            suspend=suspend, delete=delete)


register_operation(RenewOperation)


class ChangeStateOperation(InstanceOperation):
    activity_code_suffix = 'emergency_change_state'
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

    def _operation(self, user, activity, new_state="NOSTATE", interrupt=False):
        activity.resultant_state = new_state
        if interrupt:
            msg_txt = ugettext_noop("Activity is forcibly interrupted.")
            message = create_readable(msg_txt, msg_txt)
            for i in InstanceActivity.objects.filter(
                    finished__isnull=True, instance=self.instance):
                i.finish(False, result=message)
                logger.error('Forced finishing activity %s', i)


register_operation(ChangeStateOperation)


class NodeOperation(Operation):
    async_operation = abortable_async_node_operation
    host_cls = Node

    def __init__(self, node):
        super(NodeOperation, self).__init__(subject=node)
        self.node = node

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

            return parent.create_sub(code_suffix=self.activity_code_suffix,
                                     readable_name=name)
        else:
            return NodeActivity.create(code_suffix=self.activity_code_suffix,
                                       node=self.node, user=user,
                                       readable_name=name)


class FlushOperation(NodeOperation):
    activity_code_suffix = 'flush'
    id = 'flush'
    name = _("flush")
    description = _("Disable node and move all instances to other ones.")
    required_perms = ()
    superuser_required = True
    async_queue = "localhost.man.slow"

    def on_abort(self, activity, error):
        from manager.scheduler import TraitsUnsatisfiableException
        if isinstance(error, TraitsUnsatisfiableException):
            if self.node_enabled:
                self.node.enable(activity.user, activity)

    def _operation(self, activity, user):
        self.node_enabled = self.node.enabled
        self.node.disable(user, activity)
        for i in self.node.instance_set.all():
            name = create_readable(ugettext_noop(
                "migrate %(instance)s (%(pk)s)"), instance=i.name, pk=i.pk)
            with activity.sub_activity('migrate_instance_%d' % i.pk,
                                       readable_name=name):
                i.migrate(user=user)


register_operation(FlushOperation)


class ScreenshotOperation(InstanceOperation):
    activity_code_suffix = 'screenshot'
    id = 'screenshot'
    name = _("screenshot")
    description = _("Get a screenshot about the virtual machine's console. A "
                    "key will be pressed on the keyboard to stop "
                    "screensaver.")
    acl_level = "owner"
    required_perms = ()
    accept_states = ('RUNNING', )

    def _operation(self):
        return self.instance.get_screenshot(timeout=20)


register_operation(ScreenshotOperation)


class RecoverOperation(InstanceOperation):
    activity_code_suffix = 'recover'
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

    def _operation(self):
        for disk in self.instance.disks.all():
            disk.destroyed = None
            disk.restore()
            disk.save()
        self.instance.destroyed_at = None
        self.instance.save()


register_operation(RecoverOperation)


class ResourcesOperation(InstanceOperation):
    activity_code_suffix = 'Resources change'
    id = 'resources_change'
    name = _("resources change")
    description = _("Change resources of a stopped virtual machine.")
    acl_level = "owner"
    required_perms = ('vm.change_resources', )
    accept_states = ('STOPPED', 'PENDING', )

    def _operation(self, user, activity,
                   num_cores, ram_size, max_ram_size, priority):

        self.instance.num_cores = num_cores
        self.instance.ram_size = ram_size
        self.instance.max_ram_size = max_ram_size
        self.instance.priority = priority

        self.instance.full_clean()
        self.instance.save()

        activity.result = create_readable(ugettext_noop(
            "Priority: %(priority)s, Num cores: %(num_cores)s, "
            "Ram size: %(ram_size)s"), priority=priority, num_cores=num_cores,
            ram_size=ram_size
        )


register_operation(ResourcesOperation)


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
                started__gt=last_boot_time).latest("started")
        except InstanceActivity.DoesNotExist:  # no agent since last boot
            raise self.instance.NoAgentError(self.instance)


class PasswordResetOperation(EnsureAgentMixin, InstanceOperation):
    activity_code_suffix = 'password_reset'
    id = 'password_reset'
    name = _("password reset")
    description = _("Generate and set a new login password on the virtual "
                    "machine. This operation requires the agent running. "
                    "Resetting the password is not warranted to allow you "
                    "logging in as other settings are possible to prevent "
                    "it.")
    acl_level = "owner"
    required_perms = ()

    def _operation(self):
        self.instance.pw = pwgen()
        queue = self.instance.get_remote_queue_name("agent")
        agent_tasks.change_password.apply_async(
            queue=queue, args=(self.instance.vm_name, self.instance.pw))
        self.instance.save()


register_operation(PasswordResetOperation)


class MountStoreOperation(EnsureAgentMixin, InstanceOperation):
    activity_code_suffix = 'mount_store'
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


register_operation(MountStoreOperation)
