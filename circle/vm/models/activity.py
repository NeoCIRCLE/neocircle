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

from __future__ import absolute_import, unicode_literals
from contextlib import contextmanager
from logging import getLogger

from celery.signals import worker_ready
from django.core.urlresolvers import reverse
from django.db.models import CharField, ForeignKey
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from common.models import (
    ActivityModel, activitycontextimpl, join_activity_code,
)


logger = getLogger(__name__)


class ActivityInProgressError(Exception):

        def __init__(self, activity, message=None):
            if message is None:
                message = ("Another activity is currently in progress: '%s'."
                           % activity.activity_code)

            Exception.__init__(self, message)

            self.activity = activity


class InstanceActivity(ActivityModel):
    ACTIVITY_CODE_BASE = join_activity_code('vm', 'Instance')
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

    def get_absolute_url(self):
        return reverse('dashboard.views.vm-activity', args=[self.pk])

    def get_readable_name(self):
        return self.activity_code.split('.')[-1].replace('_', ' ').capitalize()

    def get_status_id(self):
        if self.succeeded is None:
            return 'wait'
        elif self.succeeded:
            return 'success'
        else:
            return 'failed'

    @classmethod
    def create(cls, code_suffix, instance, task_uuid=None, user=None,
               concurrency_check=True):
        # Check for concurrent activities
        active_activities = instance.activity_log.filter(finished__isnull=True)
        if concurrency_check and active_activities.exists():
            raise ActivityInProgressError(active_activities[0])

        activity_code = join_activity_code(cls.ACTIVITY_CODE_BASE, code_suffix)
        act = cls(activity_code=activity_code, instance=instance, parent=None,
                  resultant_state=None, started=timezone.now(),
                  task_uuid=task_uuid, user=user)
        act.save()
        return act

    def create_sub(self, code_suffix, task_uuid=None, concurrency_check=True):
        # Check for concurrent activities
        active_children = self.children.filter(finished__isnull=True)
        if concurrency_check and active_children.exists():
            raise ActivityInProgressError(active_children[0])

        act = InstanceActivity(
            activity_code=join_activity_code(self.activity_code, code_suffix),
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
    ACTIVITY_CODE_BASE = join_activity_code('vm', 'Node')
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
        activity_code = join_activity_code(cls.ACTIVITY_CODE_BASE, code_suffix)
        act = cls(activity_code=activity_code, node=node, parent=None,
                  started=timezone.now(), task_uuid=task_uuid, user=user)
        act.save()
        return act

    def create_sub(self, code_suffix, task_uuid=None):
        act = NodeActivity(
            activity_code=join_activity_code(self.activity_code, code_suffix),
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


@worker_ready.connect()
def cleanup(conf=None, **kwargs):
    # TODO check if other manager workers are running
    for i in InstanceActivity.objects.filter(finished__isnull=True):
        i.finish(False, "Manager is restarted, activity is cleaned up. "
                 "You can try again now.")
    for i in NodeActivity.objects.filter(finished__isnull=True):
        i.finish(False, "Manager is restarted, activity is cleaned up. "
                 "You can try again now.")
