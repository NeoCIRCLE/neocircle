from .models import activity_context

from django.core.exceptions import PermissionDenied


class Operation(object):
    """Base class for VM operations.
    """
    async_queue = 'localhost.man'
    required_perms = ()

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
        skip_checks = kwargs.setdefault('system', False)
        user = kwargs.setdefault('user', None)
        parent_activity = kwargs.pop('parent_activity', None)

        if not skip_checks:
            self.check_auth(user)
        self.check_precond()
        return self.create_activity(parent=parent_activity, user=user)

    def _exec_op(self, activity, user, **kwargs):
        """Execute the operation inside the specified activity's context.
        """
        with activity_context(activity, on_abort=self.on_abort,
                              on_commit=self.on_commit):
            return self._operation(activity, user, **kwargs)

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


def register_operation(target_cls, op_cls, op_id=None):
    """Register the specified operation with the target class.

    You can optionally specify an ID to be used for the registration;
    otherwise, the operation class' 'id' attribute will be used.
    """
    if op_id is None:
        op_id = op_cls.id

    if not issubclass(target_cls, OperatedMixin):
        raise TypeError("%r is not a subclass of %r" %
                        (target_cls.__name__, OperatedMixin.__name__))

    if not hasattr(target_cls, operation_registry_name):
        setattr(target_cls, operation_registry_name, dict())

    getattr(target_cls, operation_registry_name)[op_id] = op_cls
