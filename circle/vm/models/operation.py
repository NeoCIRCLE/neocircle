from __future__ import absolute_import, unicode_literals

from common.models import activity_context
from ..tasks.local_tasks import async_operation
from .activity import InstanceActivity
from .instance import Instance


class Operation:
    """Base class for VM operations.
    """
    acl_level = 'owner'
    async_queue = 'localhost.man'

    def __init__(self, instance):
        """Initialize a new operation bound to the specified VM instance.
        """
        self.instance = instance

    def __call__(self, **kwargs):
        """Execute the operation synchronously.
        """
        activity = self.__prelude(kwargs)
        return self._exec_op(activity=activity, **kwargs)

    def __unicode__(self):
        return self.name

    def __prelude(self, kwargs):
        """This method contains the shared prelude of __call__ and async.
        """
        user = kwargs.setdefault('user', None)
        self.check_auth(user)  # TODO what's check_auth's specification?
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
        pass

    def async(self, **kwargs):
        """Execute the operation asynchronously.

        Only a quick, preliminary check is ran before queuing the job.
        """
        activity = self.__prelude(kwargs)
        return async_operation.apply_async(args=(self.id, self.instance.pk,
                                                 activity.pk), kwargs=kwargs,
                                           queue=self.async_queue)

    def check_precond(self):
        pass

    def check_auth(self, user):
        pass

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
