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

from logging import getLogger

from .models import activity_context

from django.core.exceptions import PermissionDenied


logger = getLogger(__name__)


class Operation(object):
    """Base class for VM operations.
    """
    async_queue = 'localhost.man'
    required_perms = ()
    do_not_call_in_templates = True

    def __call__(self, **kwargs):
        return self.call(**kwargs)

    def __init__(self, subject):
        """Initialize a new operation bound to the specified subject.
        """
        self.subject = subject

    def __unicode__(self):
        return self.name

    def __prelude(self, kwargs):
        """This method contains the shared prelude of call and async.
        """
        skip_auth_check = kwargs.setdefault('system', False)
        user = kwargs.setdefault('user', None)
        parent_activity = kwargs.pop('parent_activity', None)

        if not skip_auth_check:
            self.check_auth(user)
        self.check_precond()
        return self.create_activity(parent=parent_activity, user=user)

    def _exec_op(self, activity, user, **kwargs):
        """Execute the operation inside the specified activity's context.
        """
        with activity_context(activity, on_abort=self.on_abort,
                              on_commit=self.on_commit):
            return self._operation(activity=activity, user=user, **kwargs)

    def _operation(self, activity, user, system, **kwargs):
        """This method is the operation's particular implementation.

        Deriving classes should implement this method.
        """
        raise NotImplementedError

    def async(self, **kwargs):
        """Execute the operation asynchronously.

        Only a quick, preliminary check is ran before creating the associated
        activity and queuing the job.

        The returned value is the handle for the asynchronous job.

        For more information, check the synchronous call's documentation.
        """
        logger.info("%s called asynchronously on %s with the following "
                    "parameters: %r", self.__class__.__name__, self.subject,
                    kwargs)
        activity = self.__prelude(kwargs)
        return self.async_operation.apply_async(args=(self.id,
                                                      self.subject.pk,
                                                      activity.pk),
                                                kwargs=kwargs,
                                                queue=self.async_queue)

    def call(self, **kwargs):
        """Execute the operation (synchronously).

        Anticipated keyword arguments:
        * parent_activity: Parent activity for the operation. If this argument
                           is present, the operation's activity will be created
                           as a child activity of it.
        * system: Indicates that the operation is invoked by the system, not a
                  User. If this argument is present and has a value of True,
                  then authorization checks are skipped.
        * user: The User invoking the operation. If this argument is not
                present, it'll be provided with a default value of None.
        """
        logger.info("%s called (synchronously) on %s with the following "
                    "parameters: %r", self.__class__.__name__, self.subject,
                    kwargs)
        activity = self.__prelude(kwargs)
        return self._exec_op(activity=activity, **kwargs)

    def check_precond(self):
        pass

    def check_auth(self, user):
        if not user.has_perms(self.required_perms):
            raise PermissionDenied("%s doesn't have the required permissions."
                                   % user)

    def create_activity(self, parent, user):
        raise NotImplementedError

    def on_abort(self, activity, error):
        """This method is called when the operation aborts (i.e. raises an
        exception).
        """
        pass

    def on_commit(self, activity):
        """This method is called when the operation executes successfully.
        """
        pass


operation_registry_name = '_ops'


class OperatedMixin(object):
    def __getattr__(self, name):
        # NOTE: __getattr__ is only called if the attribute doesn't already
        # exist in your __dict__
        cls = self.__class__
        ops = getattr(cls, operation_registry_name, {})
        op = ops.get(name)
        if op:
            return op(self)
        else:
            raise AttributeError("%r object has no attribute %r" %
                                 (self.__class__.__name__, name))

    def get_available_operations(self, user):
        """Yield Operations that match permissions of user and preconditions.
        """
        for name in getattr(self, operation_registry_name, {}):
            try:
                op = getattr(self, name)
                op.check_auth(user)
                op.check_precond()
            except:
                pass  # unavailable
            else:
                yield op


def register_operation(op_cls, op_id=None, target_cls=None):
    """Register the specified operation with the target class.

    You can optionally specify an ID to be used for the registration;
    otherwise, the operation class' 'id' attribute will be used.
    """
    if op_id is None:
        try:
            op_id = op_cls.id
        except AttributeError:
            raise NotImplementedError("Operations should specify an 'id' "
                                      "attribute designating the name the "
                                      "operation can be called by on its "
                                      "host. Alternatively, provide the name "
                                      "in the 'op_id' parameter to this call.")

    if target_cls is None:
        try:
            target_cls = op_cls.host_cls
        except AttributeError:
            raise NotImplementedError("Operations should specify a 'host_cls' "
                                      "attribute designating the host class "
                                      "the operation should be registered to. "
                                      "Alternatively, provide the host class "
                                      "in the 'target_cls' parameter to this "
                                      "call.")

    if not issubclass(target_cls, OperatedMixin):
        raise TypeError("%r is not a subclass of %r" %
                        (target_cls.__name__, OperatedMixin.__name__))

    if not hasattr(target_cls, operation_registry_name):
        setattr(target_cls, operation_registry_name, dict())

    getattr(target_cls, operation_registry_name)[op_id] = op_cls
