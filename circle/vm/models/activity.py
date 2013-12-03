from __future__ import absolute_import, unicode_literals
from contextlib import contextmanager
from logging import getLogger

from django.db.models import ForeignKey
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from common.models import ActivityModel, activitycontextimpl
logger = getLogger(__name__)


class InstanceActivity(ActivityModel):
    instance = ForeignKey('Instance', related_name='activity_log',
                          help_text=_('Instance this activity works on.'),
                          verbose_name=_('instance'))

    class Meta:
        app_label = 'vm'
        db_table = 'vm_instanceactivity'
        ordering = ['-started', 'instance', '-id']

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
                  instance=instance, parent=None, started=timezone.now(),
                  task_uuid=task_uuid, user=user)
        act.save()
        return act

    def create_sub(self, code_suffix, task_uuid=None):
        act = InstanceActivity(
            activity_code=self.activity_code + '.' + code_suffix,
            instance=self.instance, parent=self, started=timezone.now(),
            task_uuid=task_uuid, user=self.user)
        act.save()
        return act

    @contextmanager
    def sub_activity(self, code_suffix, task_uuid=None):
        act = self.create_sub(code_suffix, task_uuid)
        return activitycontextimpl(act)


@contextmanager
def instance_activity(code_suffix, instance, task_uuid=None, user=None):
    act = InstanceActivity.create(code_suffix, instance, task_uuid, user)
    return activitycontextimpl(act)


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
    act = InstanceActivity.create(code_suffix, node, task_uuid, user)
    return activitycontextimpl(act)
