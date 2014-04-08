from __future__ import absolute_import, unicode_literals
from logging import getLogger
from string import ascii_lowercase

from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from celery.exceptions import TimeLimitExceeded

from common.operations import Operation, register_operation
from storage.models import Disk
from .tasks import vm_tasks
from .tasks.local_tasks import async_instance_operation, async_node_operation
from .models import (
    Instance, InstanceActivity, InstanceTemplate, Node, NodeActivity,
)


logger = getLogger(__name__)


class InstanceOperation(Operation):
    acl_level = 'owner'
    async_operation = async_instance_operation

    def __init__(self, instance):
        super(InstanceOperation, self).__init__(subject=instance)
        self.instance = instance

    def check_precond(self):
        if self.instance.destroyed_at:
            raise self.instance.InstanceDestroyedError(self.instance)

    def check_auth(self, user):
        if not self.instance.has_level(user, self.acl_level):
            raise PermissionDenied("%s doesn't have the required ACL level." %
                                   user)

        super(InstanceOperation, self).check_auth(user=user)

    def create_activity(self, parent, user):
        if parent:
            if parent.instance != self.instance:
                raise ValueError("The instance associated with the specified "
                                 "parent activity does not match the instance "
                                 "bound to the operation.")
            if parent.user != user:
                raise ValueError("The user associated with the specified "
                                 "parent activity does not match the user "
                                 "provided as parameter.")

            return parent.create_sub(code_suffix=self.activity_code_suffix)
        else:
            return InstanceActivity.create(
                code_suffix=self.activity_code_suffix, instance=self.instance,
                user=user)


def register_instance_operation(op_cls, op_id=None):
    return register_operation(Instance, op_cls, op_id)


class DeployOperation(InstanceOperation):
    activity_code_suffix = 'deploy'
    id = 'deploy'
    name = _("deploy")
    description = _("""Deploy new virtual machine with network

        :param self: The virtual machine to deploy.
        :type self: vm.models.Instance

        :param user: The user who's issuing the command.
        :type user: django.contrib.auth.models.User

        :param task_uuid: The task's UUID, if the command is being executed
                          asynchronously.
        :type task_uuid: str
        """)

    def on_commit(self, activity):
        activity.resultant_state = 'RUNNING'

    def _operation(self, activity, user, system):
        self.instance._schedule_vm(activity)

        # Deploy virtual images
        with activity.sub_activity('deploying_disks'):
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

        self.instance._deploy_vm(activity)


register_instance_operation(DeployOperation)


class DestroyOperation(InstanceOperation):
    activity_code_suffix = 'destroy'
    id = 'destroy'
    name = _("destroy")
    description = _("""Remove virtual machine and its networks.

        :param self: The virtual machine to destroy.
        :type self: vm.models.Instance

        :param user: The user who's issuing the command.
        :type user: django.contrib.auth.models.User

        :param task_uuid: The task's UUID, if the command is being executed
                          asynchronously.
        :type task_uuid: str
        """)

    def on_commit(self, activity):
        activity.resultant_state = 'DESTROYED'

    def _operation(self, activity, user, system):
        if self.instance.node:
            self.instance._destroy_vm(activity)

        # Destroy disks
        with activity.sub_activity('destroying_disks'):
            for disk in self.instance.disks.all():
                disk.destroy()

        self.instance._cleanup_after_destroy_vm(activity)

        self.instance.destroyed_at = timezone.now()
        self.instance.save()


register_instance_operation(DestroyOperation)


class MigrateOperation(InstanceOperation):
    activity_code_suffix = 'migrate'
    id = 'migrate'
    name = _("migrate")
    description = _("""Live migrate running vm to another node.""")

    def _operation(self, activity, user, system, to_node=None, timeout=120):
        if not to_node:
            with activity.sub_activity('scheduling') as sa:
                to_node = self.instance.select_node()
                sa.result = to_node

        # Destroy networks
        with activity.sub_activity('destroying_net'):
            for net in self.instance.interface_set.all():
                net.shutdown()

        with activity.sub_activity('migrate_vm'):
            queue_name = self.instance.get_remote_queue_name('vm')
            vm_tasks.migrate.apply_async(args=[self.instance.vm_name,
                                               to_node.host.hostname],
                                         queue=queue_name).get(timeout=timeout)
        # Refresh node information
        self.instance.node = to_node
        self.instance.save()
        # Estabilish network connection (vmdriver)
        with activity.sub_activity('deploying_net'):
            for net in self.instance.interface_set.all():
                net.deploy()


register_instance_operation(MigrateOperation)


class RebootOperation(InstanceOperation):
    activity_code_suffix = 'reboot'
    id = 'reboot'
    name = _("reboot")
    description = _("""Reboot virtual machine with Ctrl+Alt+Del signal.""")

    def _operation(self, activity, user, system, timeout=5):
        queue_name = self.instance.get_remote_queue_name('vm')
        vm_tasks.reboot.apply_async(args=[self.instance.vm_name],
                                    queue=queue_name).get(timeout=timeout)


register_instance_operation(RebootOperation)


class RedeployOperation(InstanceOperation):
    activity_code_suffix = 'redeploy'
    id = 'redeploy'
    name = _("redeploy")
    description = _("""Redeploy virtual machine with network

        :param self: The virtual machine to redeploy.

        :param user: The user who's issuing the command.
        :type user: django.contrib.auth.models.User

        :param task_uuid: The task's UUID, if the command is being executed
                          asynchronously.
        :type task_uuid: str
        """)

    def _operation(self, activity, user, system):
        # Destroy VM
        if self.instance.node:
            self.instance._destroy_vm(activity)

        self.instance._cleanup_after_destroy_vm(activity)

        # Deploy VM
        self.instance._schedule_vm(activity)

        self.instance._deploy_vm(activity)


register_instance_operation(RedeployOperation)


class ResetOperation(InstanceOperation):
    activity_code_suffix = 'reset'
    id = 'reset'
    name = _("reset")
    description = _("""Reset virtual machine (reset button)""")

    def _operation(self, activity, user, system, timeout=5):
        queue_name = self.instance.get_remote_queue_name('vm')
        vm_tasks.reset.apply_async(args=[self.instance.vm_name],
                                   queue=queue_name).get(timeout=timeout)


register_instance_operation(ResetOperation)


class SaveAsTemplateOperation(InstanceOperation):
    activity_code_suffix = 'save_as_template'
    id = 'save_as_template'
    name = _("save as template")
    description = _("""Save Virtual Machine as a Template.

        Template can be shared with groups and users.
        Users can instantiate Virtual Machines from Templates.
        """)

    def _operation(self, activity, name, user, system, timeout=300,
                   with_shutdown=True, **kwargs):
        if with_shutdown:
            ShutdownOperation(self.instance).call(parent_activity=activity,
                                                  user=user)
        # prepare parameters
        params = {
            'access_method': self.instance.access_method,
            'arch': self.instance.arch,
            'boot_menu': self.instance.boot_menu,
            'description': self.instance.description,
            'lease': self.instance.lease,  # Can be problem in new VM
            'max_ram_size': self.instance.max_ram_size,
            'name': name,
            'num_cores': self.instance.num_cores,
            'owner': user,
            'parent': self.instance.template,  # Can be problem
            'priority': self.instance.priority,
            'ram_size': self.instance.ram_size,
            'raw_data': self.instance.raw_data,
            'system': self.instance.system,
        }
        params.update(kwargs)

        def __try_save_disk(disk):
            try:
                return disk.save_as()  # can do in parallel
            except Disk.WrongDiskTypeError:
                return disk

        # create template and do additional setup
        tmpl = InstanceTemplate(**params)
        tmpl.full_clean()  # Avoiding database errors.
        tmpl.save()
        try:
            with activity.sub_activity('saving_disks'):
                tmpl.disks.add(*[__try_save_disk(disk)
                                 for disk in self.instance.disks.all()])
            # create interface templates
            for i in self.instance.interface_set.all():
                i.save_as_template(tmpl)
        except:
            tmpl.delete()
            raise
        else:
            return tmpl


register_instance_operation(SaveAsTemplateOperation)


class ShutdownOperation(InstanceOperation):
    activity_code_suffix = 'shutdown'
    id = 'shutdown'
    name = _("shutdown")
    description = _("""Shutdown virtual machine with ACPI signal.""")

    def on_abort(self, activity, error):
        if isinstance(error, TimeLimitExceeded):
            activity.resultant_state = None
        else:
            activity.resultant_state = 'ERROR'

    def on_commit(self, activity):
        activity.resultant_state = 'STOPPED'

    def _operation(self, activity, user, system, timeout=120):
        queue_name = self.instance.get_remote_queue_name('vm')
        logger.debug("RPC Shutdown at queue: %s, for vm: %s.", queue_name,
                     self.instance.vm_name)
        vm_tasks.shutdown.apply_async(kwargs={'name': self.instance.vm_name},
                                      queue=queue_name).get(timeout=timeout)
        self.instance.node = None
        self.instance.vnc_port = None
        self.instance.save()


register_instance_operation(ShutdownOperation)


class ShutOffOperation(InstanceOperation):
    activity_code_suffix = 'shut_off'
    id = 'shut_off'
    name = _("shut off")
    description = _("""Shut off VM. (plug-out)""")

    def on_commit(activity):
        activity.resultant_state = 'STOPPED'

    def _operation(self, activity, user, system):
        # Destroy VM
        if self.instance.node:
            self.instance._destroy_vm(activity)

        self.instance._cleanup_after_destroy_vm(activity)
        self.instance.save()


register_instance_operation(ShutOffOperation)


class SleepOperation(InstanceOperation):
    activity_code_suffix = 'sleep'
    id = 'sleep'
    name = _("sleep")
    description = _("""Suspend virtual machine with memory dump.""")

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

    def _operation(self, activity, user, system, timeout=60):
        # Destroy networks
        with activity.sub_activity('destroying_net'):
            for net in self.instance.interface_set.all():
                net.shutdown()

        # Suspend vm
        with activity.sub_activity('suspending'):
            queue_name = self.instance.get_remote_queue_name('vm')
            vm_tasks.sleep.apply_async(args=[self.instance.vm_name,
                                             self.instance.mem_dump['path']],
                                       queue=queue_name).get(timeout=timeout)
            self.instance.node = None
            self.instance.save()


register_instance_operation(SleepOperation)


class WakeUpOperation(InstanceOperation):
    activity_code_suffix = 'wake_up'
    id = 'wake_up'
    name = _("wake up")
    description = _("""Wake up Virtual Machine from SUSPENDED state.

        Power on Virtual Machine and load its memory from dump.
        """)

    def check_precond(self):
        super(WakeUpOperation, self).check_precond()
        if self.instance.status not in ['SUSPENDED']:
            raise self.instance.WrongStateError(self.instance)

    def on_abort(self, activity, error):
        activity.resultant_state = 'ERROR'

    def on_commit(self, activity):
        activity.resultant_state = 'RUNNING'

    def _operation(self, activity, user, system, timeout=60):
        # Schedule vm
        self.instance._schedule_vm(activity)
        queue_name = self.instance.get_remote_queue_name('vm')

        # Resume vm
        with activity.sub_activity('resuming'):
            vm_tasks.wake_up.apply_async(args=[self.instance.vm_name,
                                               self.instance.mem_dump['path']],
                                         queue=queue_name).get(timeout=timeout)

        # Estabilish network connection (vmdriver)
        with activity.sub_activity('deploying_net'):
            for net in self.instance.interface_set.all():
                net.deploy()

        # Renew vm
        self.instance.renew(which='both', base_activity=activity)


register_instance_operation(WakeUpOperation)


class NodeOperation(Operation):
    async_operation = async_node_operation

    def __init__(self, node):
        super(NodeOperation, self).__init__(subject=node)
        self.node = node

    def create_activity(self, parent, user):
        if parent:
            if parent.node != self.node:
                raise ValueError("The node associated with the specified "
                                 "parent activity does not match the node "
                                 "bound to the operation.")
            if parent.user != user:
                raise ValueError("The user associated with the specified "
                                 "parent activity does not match the user "
                                 "provided as parameter.")

            return parent.create_sub(code_suffix=self.activity_code_suffix)
        else:
            return NodeActivity.create(code_suffix=self.activity_code_suffix,
                                       node=self.node, user=user)


def register_node_operation(op_cls, op_id=None):
    return register_operation(Node, op_cls, op_id)


class FlushOperation(NodeOperation):
    activity_code_suffix = 'flush'
    id = 'flush'
    name = _("flush")
    description = _("""Disable node and move all instances to other ones.""")

    def _operation(self, activity, user, system):
        self.node.disable(user, activity)
        for i in self.node.instance_set.all():
            with activity.sub_activity('migrate_instance_%d' % i.pk):
                i.migrate()


register_node_operation(FlushOperation)
