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
from warnings import warn

from celery.contrib.abortable import AbortableAsyncResult

from django.core.urlresolvers import reverse
from django.db.models import CharField, ForeignKey, BooleanField
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _, ugettext_noop

from common.models import (
    ActivityModel, activitycontextimpl, create_readable, join_activity_code,
    HumanReadableObject, HumanReadableException,
)

from manager.mancelery import celery


logger = getLogger(__name__)


class ActivityInProgressError(HumanReadableException):

    @classmethod
    def create(cls, activity):
        obj = super(ActivityInProgressError, cls).create(
            ugettext_noop("%(activity)s activity is currently in progress."),
            ugettext_noop("%(activity)s (%(pk)s) activity is currently "
                          "in progress."),
            activity=activity.readable_name, pk=activity.pk)
        obj.activity = activity
        return obj


def _normalize_readable_name(name, default=None):
    if name is None:
        warn("Set readable_name to a HumanReadableObject",
             DeprecationWarning, 3)
        name = default.replace(".", " ")

    if not isinstance(name, HumanReadableObject):
        name = create_readable(name)

    return name


class InstanceActivity(ActivityModel):
    ACTIVITY_CODE_BASE = join_activity_code('vm', 'Instance')
    instance = ForeignKey('Instance', related_name='activity_log',
                          help_text=_('Instance this activity works on.'),
                          verbose_name=_('instance'))
    resultant_state = CharField(blank=True, max_length=20, null=True)
    interruptible = BooleanField(default=False, help_text=_(
        'Other activities can interrupt this one.'))

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

    def abort(self):
        AbortableAsyncResult(self.task_uuid, backend=celery.backend).abort()

    @classmethod
    def create(cls, code_suffix, instance, task_uuid=None, user=None,
               concurrency_check=True, readable_name=None,
               resultant_state=None, interruptible=False):

        readable_name = _normalize_readable_name(readable_name, code_suffix)
        # Check for concurrent activities
        active_activities = instance.activity_log.filter(finished__isnull=True)
        if concurrency_check and active_activities.exists():
            for i in active_activities:
                if i.interruptible:
                    i.finish(False, result=ugettext_noop(
                        "Interrupted by other activity."))
                else:
                    raise ActivityInProgressError.create(i)

        activity_code = cls.construct_activity_code(code_suffix)
        act = cls(activity_code=activity_code, instance=instance, parent=None,
                  resultant_state=resultant_state, started=timezone.now(),
                  readable_name_data=readable_name.to_dict(),
                  task_uuid=task_uuid, user=user, interruptible=interruptible)
        act.save()
        return act

    def create_sub(self, code_suffix, task_uuid=None, concurrency_check=True,
                   readable_name=None, resultant_state=None,
                   interruptible=False):

        readable_name = _normalize_readable_name(readable_name, code_suffix)
        # Check for concurrent activities
        active_children = self.children.filter(finished__isnull=True)
        if concurrency_check and active_children.exists():
            raise ActivityInProgressError.create(active_children[0])

        act = InstanceActivity(
            activity_code=join_activity_code(self.activity_code, code_suffix),
            instance=self.instance, parent=self,
            resultant_state=resultant_state, interruptible=interruptible,
            readable_name_data=readable_name.to_dict(), started=timezone.now(),
            task_uuid=task_uuid, user=self.user)
        act.save()
        return act

    def get_absolute_url(self):
        return reverse('dashboard.views.vm-activity', args=[self.pk])

    def get_status_id(self):
        if self.succeeded is None:
            return 'wait'
        elif self.succeeded:
            return 'success'
        else:
            return 'failed'

    def has_percentage(self):
        op = self.instance.get_operation_from_activity_code(self.activity_code)
        return (self.task_uuid and op and op.has_percentage and
                not self.finished)

    def get_percentage(self):
        """Returns the percentage of the running operation if available.
        """
        result = celery.AsyncResult(id=self.task_uuid)
        if self.has_percentage() and result.info is not None:
            return result.info.get("percent")
        else:
            return 0

    @property
    def is_abortable(self):
        """Can the activity be aborted?

        :returns: True if the activity can be aborted; otherwise, False.
        """
        op = self.instance.get_operation_from_activity_code(self.activity_code)
        return self.task_uuid and op and op.abortable and not self.finished

    def is_abortable_for(self, user):
        """Can the given user abort the activity?
        """

        return self.is_abortable and (
            user.is_superuser or user in (self.instance.owner, self.user))

    @property
    def is_aborted(self):
        """Has the activity been aborted?

        :returns: True if the activity has been aborted; otherwise, False.
        """
        return self.task_uuid and AbortableAsyncResult(self.task_uuid
                                                       ).is_aborted()

    def save(self, *args, **kwargs):
        ret = super(InstanceActivity, self).save(*args, **kwargs)
        self.instance._update_status()
        return ret

    @contextmanager
    def sub_activity(self, code_suffix, on_abort=None, on_commit=None,
                     readable_name=None, task_uuid=None,
                     concurrency_check=True, interruptible=False):
        """Create a transactional context for a nested instance activity.
        """
        if not readable_name:
            warn("Set readable_name", stacklevel=3)
        act = self.create_sub(code_suffix, task_uuid, concurrency_check,
                              readable_name=readable_name,
                              interruptible=interruptible)
        return activitycontextimpl(act, on_abort=on_abort, on_commit=on_commit)

    def get_operation(self):
        return self.instance.get_operation_from_activity_code(
            self.activity_code)


class NodeActivity(ActivityModel):
    ACTIVITY_CODE_BASE = join_activity_code('vm', 'Node')
    node = ForeignKey('Node', related_name='activity_log',
                      help_text=_('Node this activity works on.'),
                      verbose_name=_('node'))

    class Meta:
        app_label = 'vm'
        db_table = 'vm_nodeactivity'

    def get_operation(self):
        return self.node.get_operation_from_activity_code(
            self.activity_code)

    def __unicode__(self):
        if self.parent:
            return '{}({})->{}'.format(self.parent.activity_code,
                                       self.node,
                                       self.activity_code)
        else:
            return '{}({})'.format(self.activity_code,
                                   self.node)

    @classmethod
    def create(cls, code_suffix, node, task_uuid=None, user=None,
               readable_name=None):

        readable_name = _normalize_readable_name(readable_name, code_suffix)
        activity_code = join_activity_code(cls.ACTIVITY_CODE_BASE, code_suffix)
        act = cls(activity_code=activity_code, node=node, parent=None,
                  readable_name_data=readable_name.to_dict(),
                  started=timezone.now(), task_uuid=task_uuid, user=user)
        act.save()
        return act

    def create_sub(self, code_suffix, task_uuid=None, readable_name=None):

        readable_name = _normalize_readable_name(readable_name, code_suffix)
        act = NodeActivity(
            activity_code=join_activity_code(self.activity_code, code_suffix),
            node=self.node, parent=self, started=timezone.now(),
            readable_name_data=readable_name.to_dict(), task_uuid=task_uuid,
            user=self.user)
        act.save()
        return act

    @contextmanager
    def sub_activity(self, code_suffix, task_uuid=None, readable_name=None):
        act = self.create_sub(code_suffix, task_uuid,
                              readable_name=readable_name)
        return activitycontextimpl(act)


@contextmanager
def node_activity(code_suffix, node, task_uuid=None, user=None,
                  readable_name=None):
    act = NodeActivity.create(code_suffix, node, task_uuid, user,
                              readable_name=readable_name)
    return activitycontextimpl(act)


def cleanup(conf=None, **kwargs):
    # TODO check if other manager workers are running
    msg_txt = ugettext_noop("Manager is restarted, activity is cleaned up. "
                            "You can try again now.")
    message = create_readable(msg_txt, msg_txt)
    queue_name = kwargs.get('queue_name', None)
    for i in InstanceActivity.objects.filter(finished__isnull=True):
        op = i.get_operation()
        if op and op.async_queue == queue_name:
            i.finish(False, result=message)
            logger.error('Forced finishing stale activity %s', i)
    for i in NodeActivity.objects.filter(finished__isnull=True):
        i.finish(False, result=message)
        logger.error('Forced finishing stale activity %s', i)
