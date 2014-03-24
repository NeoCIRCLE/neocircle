from __future__ import absolute_import, unicode_literals
from logging import getLogger
from string import ascii_lowercase

from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from celery.exceptions import TimeLimitExceeded

from common.models import activity_context
from storage.models import Disk
from ..tasks import vm_tasks
from ..tasks.local_tasks import async_operation
from .activity import InstanceActivity
from .instance import Instance, InstanceTemplate


logger = getLogger(__name__)


class Operation:
    """Base class for VM operations.
    """
    acl_level = 'owner'
    async_queue = 'localhost.man'
    required_perms = ()

    def __init__(self, instance):
        """Initialize a new operation bound to the specified VM instance.
        """
        self.instance = instance

    def __call__(self, **kwargs):
        return self.call(**kwargs)

    def __unicode__(self):
        return self.name

    def __prelude(self, kwargs):
        """This method contains the shared prelude of __call__ and async.
        """
        user = kwargs.setdefault('user', None)
        self.check_auth(user)
        self.check_precond()
        return self.create_activity(user=user)

    def _exec_op(self, activity, user=None, **kwargs):
        """Execute the operation inside the specified activity's context.
        """
        with activity_context(activity, on_abort=self.on_abort,
                              on_commit=self.on_commit):
            return self._operation(activity, user, **kwargs)

    def _operation(self, activity, user=None, **kwargs):
        """This method is the operation's particular implementation.

        Deriving classes should implement this method.
        """
        raise NotImplementedError

    def async(self, **kwargs):
        """Execute the operation asynchronously.

        Only a quick, preliminary check is ran before creating the associated
        activity and queuing the job.
        """
        activity = self.__prelude(kwargs)
        return async_operation.apply_async(args=(self.id, self.instance.pk,
                                                 activity.pk), kwargs=kwargs,
                                           queue=self.async_queue)

    def call(self, **kwargs):
        """Execute the operation synchronously.
        """
        activity = self.__prelude(kwargs)
        return self._exec_op(activity=activity, **kwargs)

    def check_precond(self):
        pass

    def check_auth(self, user):
        if not self.instance.has_level(user, self.acl_level):
            raise PermissionDenied("%s doesn't have the required ACL level." %
                                   user)

        if not user.has_perms(self.required_perms):
            raise PermissionDenied("%s doesn't have the required permissions."
                                   % user)

    def create_activity(self, user=None):
        return InstanceActivity.create(code_suffix=self.activity_code_suffix,
                                       instance=self.instance, user=user)

    def on_abort(self, activity, error):
        """This method is called when the operation aborts (i.e. raises an
        exception).
        """
        pass

    def on_commit(self, activity):
        """This method is called when the operation executes successfully.
        """
        pass


def register_operation(op_cls, op_id=None):
    """Register the specified operation with Instance.
    """
    if op_id is None:
        op_id = op_cls.id

    Instance._ops[op_id] = lambda inst: op_cls(inst)


class DeployOperation(Operation):
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

    def _operation(self, activity, user=None):
        if self.instance.destroyed_at:
            raise self.instance.InstanceDestroyedError(self.instance)

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


register_operation(DeployOperation)


class DestroyOperation(Operation):
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

    def check_precond(self):
        if self.instance.destroyed_at:
            raise self.instance.InstanceDestroyedError(self.instance)

    def on_commit(self, activity):
        activity.resultant_state = 'DESTROYED'

    def _operation(self, activity, user=None):
        if self.instance.node:
            self.instance._destroy_vm(activity)

        # Destroy disks
        with activity.sub_activity('destroying_disks'):
            for disk in self.instance.disks.all():
                disk.destroy()

        self.instance._cleanup_after_destroy_vm(activity)

        self.instance.destroyed_at = timezone.now()
        self.instance.save()


register_operation(DestroyOperation)


class MigrateOperation(Operation):
    activity_code_suffix = 'migrate'
    id = 'migrate'
    name = _("migrate")
    description = _("""Live migrate running vm to another node.""")

    def _operation(self, activity, to_node=None, user=None, timeout=120):
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


register_operation(MigrateOperation)


class RebootOperation(Operation):
    activity_code_suffix = 'reboot'
    id = 'reboot'
    name = _("reboot")
    description = _("""Reboot virtual machine with Ctrl+Alt+Del signal.""")

    def _operation(self, activity, user=None, timeout=5):
        queue_name = self.instance.get_remote_queue_name('vm')
        vm_tasks.reboot.apply_async(args=[self.instance.vm_name],
                                    queue=queue_name).get(timeout=timeout)


register_operation(RebootOperation)


class RedeployOperation(Operation):
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

    def _operation(self, activity, user=None):
        # Destroy VM
        if self.instance.node:
            self.instance._destroy_vm(activity)

        self.instance._cleanup_after_destroy_vm(activity)

        # Deploy VM
        self.instance._schedule_vm(activity)

        self.instance._deploy_vm(activity)


register_operation(RedeployOperation)


class ResetOperation(Operation):
    activity_code_suffix = 'reset'
    id = 'reset'
    name = _("reset")
    description = _("""Reset virtual machine (reset button)""")

    def _operation(self, activity, user=None, timeout=5):
        queue_name = self.instance.get_remote_queue_name('vm')
        vm_tasks.reset.apply_async(args=[self.instance.vm_name],
                                   queue=queue_name).get(timeout=timeout)


register_operation(ResetOperation)


class SaveAsTemplateOperation(Operation):
    activity_code_suffix = 'save_as_template'
    id = 'save_as_template'
    name = _("save as template")
    description = _("""Save Virtual Machine as a Template.

        Template can be shared with groups and users.
        Users can instantiate Virtual Machines from Templates.
        """)

    def _operation(self, activity, name, user=None, timeout=300, **kwargs):
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


register_operation(SaveAsTemplateOperation)


class ShutdownOperation(Operation):
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

    def _operation(self, activity, user=None, timeout=120):
        queue_name = self.instance.get_remote_queue_name('vm')
        logger.debug("RPC Shutdown at queue: %s, for vm: %s.",
                     self.instance.vm_name, queue_name)  # TODO param order ok?
        vm_tasks.shutdown.apply_async(kwargs={'name': self.instance.vm_name},
                                      queue=queue_name).get(timeout=timeout)
        self.instance.node = None
        self.instance.vnc_port = None
        self.instance.save()


register_operation(ShutdownOperation)


class ShutOffOperation(Operation):
    activity_code_suffix = 'shut_off'
    id = 'shut_off'
    name = _("shut off")
    description = _("""Shut off VM. (plug-out)""")

    def on_commit(activity):
        activity.resultant_state = 'STOPPED'

    def _operation(self, activity, user=None):
        # Destroy VM
        if self.instance.node:
            self.instance._destroy_vm(activity)

        self.instance._cleanup_after_destroy_vm(activity)
        self.instance.save()


register_operation(ShutOffOperation)


class SleepOperation(Operation):
    activity_code_suffix = 'sleep'
    id = 'sleep'
    name = _("sleep")
    description = _("""Suspend virtual machine with memory dump.""")

    def check_precond(self):
        if self.instance.status not in ['RUNNING']:
            raise self.instance.WrongStateError(self.instance)

    def on_abort(self, activity, error):
        if isinstance(error, TimeLimitExceeded):
            activity.resultant_state = None
        else:
            activity.resultant_state = 'ERROR'

    def on_commit(self, activity):
        activity.resultant_state = 'SUSPENDED'

    def _operation(self, activity, user=None, timeout=60):
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


register_operation(SleepOperation)


class WakeUpOperation(Operation):
    activity_code_suffix = 'wake_up'
    id = 'wake_up'
    name = _("wake up")
    description = _("""Wake up Virtual Machine from SUSPENDED state.

        Power on Virtual Machine and load its memory from dump.
        """)

    def check_precond(self):
        if self.instance.status not in ['SUSPENDED']:
            raise self.instance.WrongStateError(self.instance)

    def on_abort(self, activity, error):
        activity.resultant_state = 'ERROR'

    def on_commit(self, activity):
        activity.resultant_state = 'RUNNING'

    def _operation(self, activity, user=None, timeout=60):
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


register_operation(WakeUpOperation)
