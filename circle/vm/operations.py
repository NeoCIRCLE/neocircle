from __future__ import absolute_import, unicode_literals
from logging import getLogger

from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from celery.exceptions import TimeLimitExceeded

from common.operations import Operation, register_operation
from .tasks.local_tasks import async_instance_operation, async_node_operation
from .models import (
    Instance, InstanceActivity, InstanceTemplate, Node, NodeActivity,
)


logger = getLogger(__name__)


class InstanceOperation(Operation):
    acl_level = 'owner'
    async_operation = async_instance_operation
    host_cls = Instance

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


class DeployOperation(InstanceOperation):
    activity_code_suffix = 'deploy'
    id = 'deploy'
    name = _("deploy")
    description = _("Deploy new virtual machine with network.")

    def on_commit(self, activity):
        activity.resultant_state = 'RUNNING'

    def _operation(self, activity, user, system, timeout=15):
        # Allocate VNC port and host node
        self.instance.allocate_vnc_port()
        self.instance.allocate_node()

        # Deploy virtual images
        with activity.sub_activity('deploying_disks'):
            self.instance.deploy_disks()

        # Deploy VM on remote machine
        with activity.sub_activity('deploying_vm') as deploy_act:
            deploy_act.result = self.instance.deploy_vm(timeout=timeout)

        # Establish network connection (vmdriver)
        with activity.sub_activity('deploying_net'):
            self.instance.deploy_net()

        # Resume vm
        with activity.sub_activity('booting'):
            self.instance.resume_vm(timeout=timeout)

        self.instance.renew(which='both', base_activity=activity)


register_operation(DeployOperation)


class DestroyOperation(InstanceOperation):
    activity_code_suffix = 'destroy'
    id = 'destroy'
    name = _("destroy")
    description = _("Destroy virtual machine and its networks.")

    def on_commit(self, activity):
        activity.resultant_state = 'DESTROYED'

    def _operation(self, activity, user, system):
        if self.instance.node:
            # Destroy networks
            with activity.sub_activity('destroying_net'):
                self.instance.destroy_net()

            # Delete virtual machine
            with activity.sub_activity('destroying_vm'):
                self.instance.delete_vm()

        # Destroy disks
        with activity.sub_activity('destroying_disks'):
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

    def _operation(self, activity, user, system, to_node=None, timeout=120):
        if not to_node:
            with activity.sub_activity('scheduling') as sa:
                to_node = self.instance.select_node()
                sa.result = to_node

        # Shutdown networks
        with activity.sub_activity('shutdown_net'):
            self.instance.shutdown_net()

        with activity.sub_activity('migrate_vm'):
            self.instance.migrate_vm(to_node=to_node, timeout=timeout)

        # Refresh node information
        self.instance.node = to_node
        self.instance.save()
        # Estabilish network connection (vmdriver)
        with activity.sub_activity('deploying_net'):
            self.instance.deploy_net()


register_operation(MigrateOperation)


class RebootOperation(InstanceOperation):
    activity_code_suffix = 'reboot'
    id = 'reboot'
    name = _("reboot")
    description = _("Reboot virtual machine with Ctrl+Alt+Del signal.")

    def _operation(self, activity, user, system, timeout=5):
        self.instance.reboot_vm(timeout=timeout)


register_operation(RebootOperation)


class ResetOperation(InstanceOperation):
    activity_code_suffix = 'reset'
    id = 'reset'
    name = _("reset")
    description = _("Reset virtual machine (reset button).")

    def _operation(self, activity, user, system, timeout=5):
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

    def _operation(self, activity, name, user, system, timeout=300,
                   with_shutdown=True, **kwargs):
        if with_shutdown:
            try:
                ShutdownOperation(self.instance).call(parent_activity=activity,
                                                      user=user)
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

        from storage.models import Disk

        def __try_save_disk(disk):
            try:
                return disk.save_as()
            except Disk.WrongDiskTypeError:
                return disk

        with activity.sub_activity('saving_disks'):
            disks = [__try_save_disk(disk)
                     for disk in self.instance.disks.all()]

        # create template and do additional setup
        tmpl = InstanceTemplate(**params)
        tmpl.full_clean()  # Avoiding database errors.
        tmpl.save()
        try:
            tmpl.disks.add(*disks)
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

    def check_precond(self):
        super(ShutdownOperation, self).check_precond()
        if self.instance.status not in ['RUNNING']:
            raise self.instance.WrongStateError(self.instance)

    def on_abort(self, activity, error):
        if isinstance(error, TimeLimitExceeded):
            activity.resultant_state = None
        else:
            activity.resultant_state = 'ERROR'

    def on_commit(self, activity):
        activity.resultant_state = 'STOPPED'

    def _operation(self, activity, user, system, timeout=120):
        self.instance.shutdown_vm(timeout=timeout)
        self.instance.yield_node()
        self.instance.yield_vnc_port()


register_operation(ShutdownOperation)


class ShutOffOperation(InstanceOperation):
    activity_code_suffix = 'shut_off'
    id = 'shut_off'
    name = _("shut off")
    description = _("Shut off VM (plug-out).")

    def on_commit(self, activity):
        activity.resultant_state = 'STOPPED'

    def _operation(self, activity, user, system):
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
        with activity.sub_activity('shutdown_net'):
            self.instance.shutdown_net()

        # Suspend vm
        with activity.sub_activity('suspending'):
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
        self.instance.allocate_vnc_port()
        self.instance.allocate_node()

        # Resume vm
        with activity.sub_activity('resuming'):
            self.instance.wake_up_vm(timeout=timeout)

        # Estabilish network connection (vmdriver)
        with activity.sub_activity('deploying_net'):
            self.instance.deploy_net()

        # Renew vm
        self.instance.renew(which='both', base_activity=activity)


register_operation(WakeUpOperation)


class NodeOperation(Operation):
    async_operation = async_node_operation
    host_cls = Node

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


class FlushOperation(NodeOperation):
    activity_code_suffix = 'flush'
    id = 'flush'
    name = _("flush")
    description = _("Disable node and move all instances to other ones.")

    def _operation(self, activity, user, system):
        self.node.disable(user, activity)
        for i in self.node.instance_set.all():
            with activity.sub_activity('migrate_instance_%d' % i.pk):
                i.migrate()


register_operation(FlushOperation)
