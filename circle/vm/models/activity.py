from __future__ import absolute_import, unicode_literals
from contextlib import contextmanager
from logging import getLogger

from django.db.models import CharField, ForeignKey
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from common.models import ActivityModel, activitycontextimpl
logger = getLogger(__name__)


class ActivityInProgressError(Exception):

        def __init__(self, activity, message=None):
            if message is None:
                message = ("Another activity is currently in progress: '%s'."
                           % activity.activity_code)

            Exception.__init__(self, message)

            self.activity = activity


class InstanceActivity(ActivityModel):
    instance = ForeignKey('Instance', related_name='activity_log',
                          help_text=_('Instance this activity works on.'),
                          verbose_name=_('instance'))
    resultant_state = CharField(blank=True, max_length=20, null=True)

    class Meta:
        app_label = 'vm'
        db_table = 'vm_instanceactivity'
        ordering = ['-finished', '-started', 'instance', '-id']

    def __unicode__(self):
        if self.parent:
            return '{}({})->{}'.format(self.parent.activity_code,
                                       self.instance,
                                       self.activity_code)
        else:
            return '{}({})'.format(self.activity_code,
                                   self.instance)

    def get_readable_name(self):
        return self.activity_code.split('.')[-1].replace('_', ' ').capitalize()

    @classmethod
    def create(cls, code_suffix, instance, task_uuid=None, user=None,
               concurrency_check=True):
        # Check for concurrent activities
        active_activities = instance.activity_log.filter(finished__isnull=True)
        if concurrency_check and active_activities.exists():
            raise ActivityInProgressError(active_activities[0])

        act = cls(activity_code='vm.Instance.' + code_suffix,
                  instance=instance, parent=None, resultant_state=None,
                  started=timezone.now(), task_uuid=task_uuid, user=user)
        act.save()
        return act

    def create_sub(self, code_suffix, task_uuid=None, concurrency_check=True):
        # Check for concurrent activities
        active_children = self.children.filter(finished__isnull=True)
        if concurrency_check and active_children.exists():
            raise ActivityInProgressError(active_children[0])

        act = InstanceActivity(
            activity_code=self.activity_code + '.' + code_suffix,
            instance=self.instance, parent=self, resultant_state=None,
            started=timezone.now(), task_uuid=task_uuid, user=self.user)
        act.save()
        return act

    @contextmanager
    def sub_activity(self, code_suffix, on_abort=None, on_commit=None,
                     task_uuid=None, concurrency_check=True):
        """Create a transactional context for a nested instance activity.
        """
        act = self.create_sub(code_suffix, task_uuid, concurrency_check)
        return activitycontextimpl(act, on_abort=on_abort, on_commit=on_commit)

    def save(self, *args, **kwargs):
        ret = super(InstanceActivity, self).save(*args, **kwargs)
        self.instance._update_status()
        return ret


@contextmanager
def instance_activity(code_suffix, instance, on_abort=None, on_commit=None,
                      task_uuid=None, user=None, concurrency_check=True):
    """Create a transactional context for an instance activity.
    """
    act = InstanceActivity.create(code_suffix, instance, task_uuid, user,
                                  concurrency_check)
    return activitycontextimpl(act, on_abort=on_abort, on_commit=on_commit)


class NodeActivity(ActivityModel):
    node = ForeignKey('Node', related_name='activity_log',
                      help_text=_('Node this activity works on.'),
                      verbose_name=_('node'))

    class Meta:
        app_label = 'vm'
        db_table = 'vm_nodeactivity'

    def __unicode__(self):
        if self.parent:
            return '{}({})->{}'.format(self.parent.activity_code,
                                       self.node,
                                       self.activity_code)
        else:
            return '{}({})'.format(self.activity_code,
                                   self.node)

    def get_readable_name(self):
        return self.activity_code.split('.')[-1].replace('_', ' ').capitalize()

    @classmethod
    def create(cls, code_suffix, node, task_uuid=None, user=None):
        act = cls(activity_code='vm.Node.' + code_suffix,
                  node=node, parent=None, started=timezone.now(),
                  task_uuid=task_uuid, user=user)
        act.save()
        return act

    def create_sub(self, code_suffix, task_uuid=None):
        act = NodeActivity(
            activity_code=self.activity_code + '.' + code_suffix,
            node=self.node, parent=self, started=timezone.now(),
            task_uuid=task_uuid, user=self.user)
        act.save()
        return act

    @contextmanager
    def sub_activity(self, code_suffix, task_uuid=None):
        act = self.create_sub(code_suffix, task_uuid)
        return activitycontextimpl(act)


@contextmanager
def node_activity(code_suffix, node, task_uuid=None, user=None):
    act = NodeActivity.create(code_suffix, node, task_uuid, user)
    return activitycontextimpl(act)
