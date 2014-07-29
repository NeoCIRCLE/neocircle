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

from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _, ugettext_noop

from celery.exceptions import TimeLimitExceeded

from common.models import create_readable, humanize_exception
from common.operations import Operation, register_operation
from .tasks.local_tasks import (
    abortable_async_instance_operation, abortable_async_node_operation,
)
from .models import (
    Instance, InstanceActivity, InstanceTemplate, Interface, Node,
    NodeActivity, pwgen
)
from .tasks import agent_tasks

logger = getLogger(__name__)


class InstanceOperation(Operation):
    acl_level = 'owner'
    async_operation = abortable_async_instance_operation
    host_cls = Instance
    concurrency_check = True

    def __init__(self, instance):
        super(InstanceOperation, self).__init__(subject=instance)
        self.instance = instance

    def check_precond(self):
        if self.instance.destroyed_at:
            raise self.instance.InstanceDestroyedError(self.instance)

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
                                     readable_name=name)
        else:
            return InstanceActivity.create(
                code_suffix=self.activity_code_suffix, instance=self.instance,
                readable_name=name, user=user,
                concurrency_check=self.concurrency_check)

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

    def rollback(self, net, activity):
        with activity.sub_activity(
            'destroying_net',
                readable_name=ugettext_noop("destroy network (rollback)")):
            net.destroy()
            net.delete()

    def check_precond(self):
        super(AddInterfaceOperation, self).check_precond()
        if self.instance.status not in ['STOPPED', 'PENDING', 'RUNNING']:
            raise self.instance.WrongStateError(self.instance)

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
                with activity.sub_activity('attach_network'):
                    self.instance.attach_network(net)
            except Exception as e:
                if hasattr(e, 'libvirtError'):
                    self.rollback(net, activity)
                raise
            net.deploy()

    def get_activity_name(self, kwargs):
        return create_readable(ugettext_noop("add %(vlan)s interface"),
                               vlan=kwargs['vlan'])


register_operation(AddInterfaceOperation)


class CreateDiskOperation(InstanceOperation):

    activity_code_suffix = 'create_disk'
    id = 'create_disk'
    name = _("create disk")
    description = _("Create empty disk for the VM.")
    required_perms = ('storage.create_empty_disk', )

    def check_precond(self):
        super(CreateDiskOperation, self).check_precond()
        if self.instance.status not in ['STOPPED', 'PENDING', 'RUNNING']:
            raise self.instance.WrongStateError(self.instance)

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
            with activity.sub_activity('deploying_disk'):
                disk.deploy()
            with activity.sub_activity('attach_disk'):
                self.instance.attach_disk(disk)

    def get_activity_name(self, kwargs):
        return create_readable(ugettext_noop("create %(size)s disk"),
                               size=kwargs['size'])


register_operation(CreateDiskOperation)


class DownloadDiskOperation(InstanceOperation):
    activity_code_suffix = 'download_disk'
    id = 'download_disk'
    name = _("download disk")
    description = _("Download disk for the VM.")
    abortable = True
    has_percentage = True
    required_perms = ('storage.download_disk', )

    def check_precond(self):
        super(DownloadDiskOperation, self).check_precond()
        if self.instance.status not in ['STOPPED', 'PENDING', 'RUNNING']:
            raise self.instance.WrongStateError(self.instance)

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
            with activity.sub_activity('attach_disk'):
                self.instance.attach_disk(disk)

register_operation(DownloadDiskOperation)


class DeployOperation(InstanceOperation):
    activity_code_suffix = 'deploy'
    id = 'deploy'
    name = _("deploy")
    description = _("Deploy new virtual machine with network.")
    required_perms = ()

    def check_precond(self):
        super(DeployOperation, self).check_precond()
        if self.instance.status in ['RUNNING', 'SUSPENDED']:
            raise self.instance.WrongStateError(self.instance)

    def is_preferred(self):
        return self.instance.status in (self.instance.STATUS.STOPPED,
                                        self.instance.STATUS.PENDING,
                                        self.instance.STATUS.ERROR)

    def on_commit(self, activity):
        activity.resultant_state = 'RUNNING'

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
            with activity.sub_activity(
                'deploying_vm', readable_name=ugettext_noop(
                    "deploy virtual machine")) as deploy_act:
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

        self.instance.renew(parent_activity=activity)


register_operation(DeployOperation)


class DestroyOperation(InstanceOperation):
    activity_code_suffix = 'destroy'
    id = 'destroy'
    name = _("destroy")
    description = _("Destroy virtual machine and its networks.")
    required_perms = ()

    def on_commit(self, activity):
        activity.resultant_state = 'DESTROYED'

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
    description = _("Live migrate running VM to another node.")
    required_perms = ()

    def rollback(self, activity):
        with activity.sub_activity(
            'rollback_net', readable_name=ugettext_noop(
                "redeploy network (rollback)")):
            self.instance.deploy_net()

    def check_precond(self):
        super(MigrateOperation, self).check_precond()
        if self.instance.status not in ['RUNNING']:
            raise self.instance.WrongStateError(self.instance)

    def check_auth(self, user):
        if not user.is_superuser:
            raise PermissionDenied()

        super(MigrateOperation, self).check_auth(user=user)

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
    description = _("Reboot virtual machine with Ctrl+Alt+Del signal.")
    required_perms = ()

    def check_precond(self):
        super(RebootOperation, self).check_precond()
        if self.instance.status not in ['RUNNING']:
            raise self.instance.WrongStateError(self.instance)

    def _operation(self, timeout=5):
        self.instance.reboot_vm(timeout=timeout)


register_operation(RebootOperation)


class RemoveInterfaceOperation(InstanceOperation):
    activity_code_suffix = 'remove_interface'
    id = 'remove_interface'
    name = _("remove interface")
    description = _("Remove the specified network interface from the VM.")
    required_perms = ()

    def check_precond(self):
        super(RemoveInterfaceOperation, self).check_precond()
        if self.instance.status not in ['STOPPED', 'PENDING', 'RUNNING']:
            raise self.instance.WrongStateError(self.instance)

    def _operation(self, activity, user, system, interface):
        if self.instance.is_running:
            with activity.sub_activity('detach_network'):
                self.instance.detach_network(interface)
            interface.shutdown()

        interface.destroy()
        interface.delete()


register_operation(RemoveInterfaceOperation)


class RemoveDiskOperation(InstanceOperation):
    activity_code_suffix = 'remove_disk'
    id = 'remove_disk'
    name = _("remove disk")
    description = _("Remove the specified disk from the VM.")
    required_perms = ()

    def check_precond(self):
        super(RemoveDiskOperation, self).check_precond()
        if self.instance.status not in ['STOPPED', 'PENDING', 'RUNNING']:
            raise self.instance.WrongStateError(self.instance)

    def _operation(self, activity, user, system, disk):
        if self.instance.is_running and disk.type not in ["iso"]:
            with activity.sub_activity('detach_disk'):
                self.instance.detach_disk(disk)
        return self.instance.disks.remove(disk)


register_operation(RemoveDiskOperation)


class ResetOperation(InstanceOperation):
    activity_code_suffix = 'reset'
    id = 'reset'
    name = _("reset")
    description = _("Reset virtual machine (reset button).")
    required_perms = ()

    def check_precond(self):
        super(ResetOperation, self).check_precond()
        if self.instance.status not in ['RUNNING']:
            raise self.instance.WrongStateError(self.instance)

    def _operation(self, timeout=5):
        self.instance.reset_vm(timeout=timeout)

register_operation(ResetOperation)


class SaveAsTemplateOperation(InstanceOperation):
    activity_code_suffix = 'save_as_template'
    id = 'save_as_template'
    name = _("save as template")
    description = _("""Save Virtual Machine as a Template.

        Template can be shared with groups and users.
        Users can instantiate Virtual Machines from Templates.
        """)
    abortable = True
    required_perms = ('vm.create_template', )

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

    def check_precond(self):
        super(SaveAsTemplateOperation, self).check_precond()
        if self.instance.status not in ['RUNNING', 'PENDING', 'STOPPED']:
            raise self.instance.WrongStateError(self.instance)

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
        with activity.sub_activity('saving_disks',
                                   readable_name=ugettext_noop("save disks")):
            for disk in self.instance.disks.all():
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
    description = _("Shutdown virtual machine with ACPI signal.")
    abortable = True
    required_perms = ()

    def check_precond(self):
        super(ShutdownOperation, self).check_precond()
        if self.instance.status not in ['RUNNING']:
            raise self.instance.WrongStateError(self.instance)

    def on_commit(self, activity):
        activity.resultant_state = 'STOPPED'

    def _operation(self, task=None):
        self.instance.shutdown_vm(task=task)
        self.instance.yield_node()
        self.instance.yield_vnc_port()


register_operation(ShutdownOperation)


class ShutOffOperation(InstanceOperation):
    activity_code_suffix = 'shut_off'
    id = 'shut_off'
    name = _("shut off")
    description = _("Shut off VM (plug-out).")
    required_perms = ()

    def check_precond(self):
        super(ShutOffOperation, self).check_precond()
        if self.instance.status not in ['RUNNING']:
            raise self.instance.WrongStateError(self.instance)

    def on_commit(self, activity):
        activity.resultant_state = 'STOPPED'

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
    description = _("Suspend virtual machine with memory dump.")
    required_perms = ()

    def is_preferred(self):
        return (not self.instance.is_base and
                self.instance.status == self.instance.STATUS.RUNNING)

    def check_precond(self):
        super(SleepOperation, self).check_precond()
        if self.instance.status not in ['RUNNING']:
            raise self.instance.WrongStateError(self.instance)

    def on_abort(self, activity, error):
        if isinstance(error, TimeLimitExceeded):
            activity.resultant_state = None
        else:
            activity.resultant_state = 'ERROR'

    def on_commit(self, activity):
        activity.resultant_state = 'SUSPENDED'

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
    description = _("""Wake up Virtual Machine from SUSPENDED state.

        Power on Virtual Machine and load its memory from dump.
        """)
    required_perms = ()

    def is_preferred(self):
        return self.instance.status == self.instance.STATUS.SUSPENDED

    def check_precond(self):
        super(WakeUpOperation, self).check_precond()
        if self.instance.status not in ['SUSPENDED']:
            raise self.instance.WrongStateError(self.instance)

    def on_abort(self, activity, error):
        activity.resultant_state = 'ERROR'

    def on_commit(self, activity):
        activity.resultant_state = 'RUNNING'

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

        # Renew vm
        self.instance.renew(parent_activity=activity)


register_operation(WakeUpOperation)


class RenewOperation(InstanceOperation):
    activity_code_suffix = 'renew'
    id = 'renew'
    name = _("renew")
    description = _("Renew expiration times")
    acl_level = "operator"
    required_perms = ()
    concurrency_check = False

    def check_precond(self):
        super(RenewOperation, self).check_precond()
        if self.instance.status == 'DESTROYED':
            raise self.instance.WrongStateError(self.instance)

    def _operation(self, lease=None):
        (self.instance.time_of_suspend,
         self.instance.time_of_delete) = self.instance.get_renew_times(lease)
        self.instance.save()


register_operation(RenewOperation)


class ChangeStateOperation(InstanceOperation):
    activity_code_suffix = 'emergency_change_state'
    id = 'emergency_change_state'
    name = _("emergency change state")
    description = _("Change the virtual machine state to NOSTATE")
    acl_level = "owner"
    required_perms = ('vm.emergency_change_state', )

    def _operation(self, user, activity, new_state="NOSTATE"):
        activity.resultant_state = new_state


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

    def on_abort(self, activity, error):
        from manager.scheduler import TraitsUnsatisfiableException
        if isinstance(error, TraitsUnsatisfiableException):
            if self.node_enabled:
                self.node.enable(activity.user, activity)

    def check_auth(self, user):
        if not user.is_superuser:
            raise humanize_exception(ugettext_noop(
                "Superuser privileges are required."), PermissionDenied())

        super(FlushOperation, self).check_auth(user=user)

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
    description = _("Get screenshot")
    acl_level = "owner"
    required_perms = ()

    def check_precond(self):
        super(ScreenshotOperation, self).check_precond()
        if self.instance.status not in ['RUNNING']:
            raise self.instance.WrongStateError(self.instance)

    def _operation(self):
        return self.instance.get_screenshot(timeout=20)


register_operation(ScreenshotOperation)


class RecoverOperation(InstanceOperation):
    activity_code_suffix = 'recover'
    id = 'recover'
    name = _("recover")
    description = _("Recover virtual machine from destroyed state.")
    acl_level = "owner"
    required_perms = ('vm.recover', )

    def check_precond(self):
        if not self.instance.destroyed_at:
            raise self.instance.WrongStateError(self.instance)

    def on_commit(self, activity):
        activity.resultant_state = 'PENDING'

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
    description = _("Change resources")
    acl_level = "owner"
    required_perms = ('vm.change_resources', )

    def check_precond(self):
        super(ResourcesOperation, self).check_precond()
        if self.instance.status not in ["STOPPED", "PENDING"]:
            raise self.instance.WrongStateError(self.instance)

    def _operation(self, user, num_cores, ram_size, max_ram_size, priority):

        self.instance.num_cores = num_cores
        self.instance.ram_size = ram_size
        self.instance.max_ram_size = max_ram_size
        self.instance.priority = priority

        self.instance.full_clean()
        self.instance.save()


register_operation(ResourcesOperation)


class PasswordResetOperation(InstanceOperation):
    activity_code_suffix = 'Password reset'
    id = 'password_reset'
    name = _("password reset")
    description = _("Password reset")
    acl_level = "owner"
    required_perms = ()

    def check_precond(self):
        super(PasswordResetOperation, self).check_precond()
        if self.instance.status not in ["RUNNING"]:
            raise self.instance.WrongStateError(self.instance)

    def _operation(self):
        self.instance.pw = pwgen()
        queue = self.instance.get_remote_queue_name("agent")
        agent_tasks.change_password.apply_async(
            queue=queue, args=(self.instance.vm_name, self.instance.pw))
        self.instance.save()


register_operation(PasswordResetOperation)
