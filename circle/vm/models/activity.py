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
    def create(cls, code_suffix, instance, task_uuid=None, user=None):
        act = cls(activity_code='vm.Instance.' + code_suffix,
                  instance=instance, parent=None, resultant_state=None,
                  started=timezone.now(), task_uuid=task_uuid, user=user)
        act.save()
        return act

    def create_sub(self, code_suffix, task_uuid=None):
        act = InstanceActivity(
            activity_code=self.activity_code + '.' + code_suffix,
            instance=self.instance, parent=self, resultant_state=None,
            started=timezone.now(), task_uuid=task_uuid, user=self.user)
        act.save()
        return act

    @contextmanager
    def sub_activity(self, code_suffix, on_abort=None, on_commit=None,
                     task_uuid=None):

        # Check for concurrent activities
        active_children = self.children.filter(finished__isnull=True)
        if active_children.exists():
            raise ActivityInProgressError(active_children[0])

        act = self.create_sub(code_suffix, task_uuid)

        return activitycontextimpl(act, on_abort=on_abort, on_commit=on_commit)


@contextmanager
def instance_activity(code_suffix, instance, on_abort=None, on_commit=None,
                      task_uuid=None, user=None):

    # Check for concurrent activities
    active_activities = instance.activity_log.filter(finished__isnull=True)
    if active_activities.exists():
        raise ActivityInProgressError(active_activities[0])

    act = InstanceActivity.create(code_suffix, instance, task_uuid, user)

    return activitycontextimpl(act, on_abort=on_abort, on_commit=on_commit)


class NodeActivity(ActivityModel):
    node = ForeignKey('Node', related_name='activity_log',
                      help_text=_('Node this activity works on.'),
                      verbose_name=_('node'))

    class Meta:
        app_label = 'vm'
        db_table = 'vm_nodeactivity'

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
