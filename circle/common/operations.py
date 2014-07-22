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

from inspect import getargspec
from logging import getLogger

from .models import activity_context, has_suffix

from django.core.exceptions import PermissionDenied, ImproperlyConfigured


logger = getLogger(__name__)


class Operation(object):
    """Base class for VM operations.
    """
    async_queue = 'localhost.man'
    required_perms = None
    do_not_call_in_templates = True
    abortable = False
    has_percentage = False

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
        defaults = {'parent_activity': None, 'system': False, 'user': None}

        allargs = dict(defaults, **kwargs)  # all arguments
        auxargs = allargs.copy()  # auxiliary (i.e. only for _operation) args
        # NOTE: consumed items should be removed from auxargs, and no new items
        # should be added to it

        skip_auth_check = auxargs.pop('system')
        user = auxargs.pop('user')
        parent_activity = auxargs.pop('parent_activity')
        if parent_activity and user is None and not skip_auth_check:
            user = parent_activity.user

        # check for unexpected keyword arguments
        argspec = getargspec(self._operation)
        if argspec.keywords is None:  # _operation doesn't take ** args
            unexpected_kwargs = set(auxargs) - set(argspec.args)
            if unexpected_kwargs:
                raise TypeError("Operation got unexpected keyword arguments: "
                                "%s" % ", ".join(unexpected_kwargs))

        if not skip_auth_check:
            self.check_auth(user)
        self.check_precond()

        activity = self.create_activity(
            parent=parent_activity, user=user, kwargs=kwargs)

        return activity, allargs, auxargs

    def _exec_op(self, allargs, auxargs):
        """Execute the operation inside the specified activity's context.
        """
        # compile arguments for _operation
        argspec = getargspec(self._operation)
        if argspec.keywords is not None:  # _operation takes ** args
            arguments = allargs.copy()
        else:  # _operation doesn't take ** args
            arguments = {k: v for (k, v) in allargs.iteritems()
                         if k in argspec.args}
        arguments.update(auxargs)

        with activity_context(allargs['activity'], on_abort=self.on_abort,
                              on_commit=self.on_commit):
            return self._operation(**arguments)

    def _operation(self, **kwargs):
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
        activity, allargs, auxargs = self.__prelude(kwargs)
        return self.async_operation.apply_async(
            args=(self.id, self.subject.pk, activity.pk, allargs, auxargs, ),
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
        activity, allargs, auxargs = self.__prelude(kwargs)
        allargs['activity'] = activity
        return self._exec_op(allargs, auxargs)

    def check_precond(self):
        pass

    def check_auth(self, user):
        if self.required_perms is None:
            raise ImproperlyConfigured(
                "Set required_perms to () if none needed.")
        if not user.has_perms(self.required_perms):
            raise PermissionDenied("%s doesn't have the required permissions."
                                   % user)

    def create_activity(self, parent, user, kwargs):
        raise NotImplementedError

    def on_abort(self, activity, error):
        """This method is called when the operation aborts (i.e. raises an
        exception).
        """
        pass

    def get_activity_name(self, kwargs):
        try:
            return self.activity_name
        except AttributeError:
            try:
                return self.name._proxy____args[0]  # ewww!
            except AttributeError:
                raise ImproperlyConfigured(
                    "Set Operation.activity_name to an ugettext_nooped "
                    "string or a create_readable call, or override "
                    "get_activity_name to create a name dynamically")

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
            op = getattr(self, name)
            try:
                op.check_auth(user)
                op.check_precond()
            except:
                pass  # unavailable
            else:
                yield op

    def get_operation_from_activity_code(self, activity_code):
        """Get an instance of the Operation corresponding to the specified
           activity code.

        :returns: A bound instance of an operation, or None if no matching
                  operation could be found.
        """
        for op in getattr(self, operation_registry_name, {}).itervalues():
            if has_suffix(activity_code, op.activity_code_suffix):
                return op(self)
        else:
            return None


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
