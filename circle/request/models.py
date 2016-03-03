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
import json
import logging

from django.db.models import (
    Model, CharField, IntegerField, TextField, ForeignKey, ManyToManyField,
)
from django.db.models.signals import post_save
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils.translation import (
    ugettext_lazy as _, ugettext_noop, ungettext
)
from django.core.urlresolvers import reverse

import requests
from sizefield.models import FileSizeField
from model_utils.models import TimeStampedModel
from model_utils import Choices
from sizefield.utils import filesizeformat

from vm.models import Instance, InstanceTemplate, Lease
from vm.operations import ResourcesOperation, ResizeDiskOperation
from storage.models import Disk

logger = logging.getLogger(__name__)


class RequestAction(Model):

    def accept(self):
        raise NotImplementedError

    @property
    def accept_msg(self):
        raise NotImplementedError

    def is_acceptable(self):
        return True

    class Meta:
        abstract = True


class RequestType(Model):
    name = CharField(max_length=100, verbose_name=_("Name"))

    def __unicode__(self):
        return self.name

    class Meta:
        abstract = True


class Request(TimeStampedModel):
    STATUSES = Choices(
        ('PENDING', _('pending')),
        ('ACCEPTED', _('accepted')),
        ('DECLINED', _('declined')),
    )
    status = CharField(choices=STATUSES, default=STATUSES.PENDING,
                       max_length=10)
    user = ForeignKey(User, related_name="user")
    closed_by = ForeignKey(User, related_name="closed_by", null=True)
    TYPES = Choices(
        ('resource', _('resource request')),
        ('lease', _("lease request")),
        ('template', _("template access request")),
        ('resize', _("disk resize request")),
    )
    type = CharField(choices=TYPES, max_length=10)
    message = TextField(verbose_name=_("Message"))
    reason = TextField(verbose_name=_("Reason"))

    content_type = ForeignKey(ContentType)
    object_id = IntegerField()
    action = GenericForeignKey("content_type", "object_id")

    def get_absolute_url(self):
        return reverse("request.views.request-detail", kwargs={'pk': self.pk})

    def get_readable_status(self):
        return self.STATUSES[self.status]

    def get_readable_type(self):
        return self.TYPES[self.type]

    def get_request_icon(self):
        return {
            'resource': "tasks",
            'lease': "clock-o",
            'template': "puzzle-piece",
            'resize': "arrows-alt",
        }.get(self.type)

    def get_effect(self):
        return {
            "PENDING": "warning",
            "ACCEPTED": "success",
            "DECLINED": "danger",
        }.get(self.status)

    def get_status_icon(self):
        return {
            "PENDING": "exclamation-triangle",
            "ACCEPTED": "check",
            "DECLINED": "times",
        }.get(self.status)

    def accept(self, user):
        self.action.accept(user)
        self.status = "ACCEPTED"
        self.closed_by = user
        self.save()

        self.user.profile.notify(
            ugettext_noop("Request accepted"),
            self.action.accept_msg
        )

    def decline(self, user, reason):
        self.status = "DECLINED"
        self.closed_by = user
        self.reason = reason
        self.save()

        decline_msg = ugettext_noop(
            'Your <a href="%(url)s">request</a> was declined because of the '
            'following reason: %(reason)s'
        )

        self.user.profile.notify(
            ugettext_noop("Request declined"),
            decline_msg, url=self.get_absolute_url(), reason=self.reason,
        )

    @property
    def is_acceptable(self):
        return self.action.is_acceptable()


class LeaseType(RequestType):
    lease = ForeignKey(Lease, verbose_name=_("Lease"))

    def __unicode__(self):
        return _("%(name)s (suspend: %(s)s, remove: %(r)s)") % {
            'name': self.name,
            's': self.lease.get_readable_suspend_time(),
            'r': self.lease.get_readable_delete_time()}

    def get_absolute_url(self):
        return reverse("request.views.lease-type-detail",
                       kwargs={'pk': self.pk})


class TemplateAccessType(RequestType):
    templates = ManyToManyField(InstanceTemplate, verbose_name=_("Templates"))

    def get_absolute_url(self):
        return reverse("request.views.template-type-detail",
                       kwargs={'pk': self.pk})


class ResourceChangeAction(RequestAction):
    instance = ForeignKey(Instance)
    num_cores = IntegerField(verbose_name=_('number of cores'),
                             help_text=_('Number of virtual CPU cores '
                                         'available to the virtual machine.'),
                             validators=[MinValueValidator(0)])
    ram_size = IntegerField(verbose_name=_('RAM size'),
                            help_text=_('Mebibytes of memory.'),
                            validators=[MinValueValidator(0)])
    priority = IntegerField(verbose_name=_('priority'),
                            help_text=_('CPU priority.'),
                            validators=[MinValueValidator(0)])

    def accept(self, user):
        self.instance.resources_change.async(
            user=user, num_cores=self.num_cores, ram_size=self.ram_size,
            max_ram_size=self.ram_size, priority=self.priority,
            with_shutdown=True)

    @property
    def accept_msg(self):
        return _(
            'The resources of <a href="%(url)s">%(name)s</a> were changed. '
            'Number of cores: %(num_cores)d, RAM size: '
            '<span class="nowrap">%(ram_size)d MiB</span>, '
            'CPU priority: %(priority)d/100.'
        ) % {
            'url': self.instance.get_absolute_url(),
            'name': self.instance.name,
            'num_cores': self.num_cores,
            'ram_size': self.ram_size,
            'priority': self.priority,
        }

    def is_acceptable(self):
        return self.instance.status in ResourcesOperation.accept_states


class ExtendLeaseAction(RequestAction):
    instance = ForeignKey(Instance)
    lease_type = ForeignKey(LeaseType)

    def accept(self, user):
        self.instance.renew(lease=self.lease_type.lease, save=True, force=True,
                            user=user)

    @property
    def accept_msg(self):
        return _(
            'The lease of <a href="%(url)s">%(name)s</a> got extended. '
            '(suspend: %(suspend)s, remove: %(remove)s)'
        ) % {'name': self.instance.name,
             'url': self.instance.get_absolute_url(),
             'suspend': self.lease_type.lease.get_readable_suspend_time(),
             'remove': self.lease_type.lease.get_readable_delete_time(), }


class TemplateAccessAction(RequestAction):
    template_type = ForeignKey(TemplateAccessType)
    LEVELS = Choices(
        ('user', _('user')),
        ('operator', _('operator')),
    )
    level = CharField(choices=LEVELS, default=LEVELS.user,
                      max_length=10)
    user = ForeignKey(User)

    def get_readable_level(self):
        return self.LEVELS[self.level]

    def accept(self, user):
        for t in self.template_type.templates.all():
            t.set_user_level(self.user, self.level)

    @property
    def accept_msg(self):
        return ungettext(
            "You got access to the following template: %s",
            "You got access to the following templates: %s",
            self.template_type.templates.count()
        ) % ", ".join([x.name for x in self.template_type.templates.all()])


class DiskResizeAction(RequestAction):
    instance = ForeignKey(Instance)
    disk = ForeignKey(Disk)
    size = FileSizeField(null=True, default=None)

    def accept(self, user):
        self.instance.resize_disk(disk=self.disk, size=self.size, user=user)

    @property
    def accept_msg(self):
        return _(
            'The disk <em class="text-muted">%(disk_name)s (#%(id)d)</em> of '
            '<a href="%(url)s">%(vm_name)s</a> got resized. '
            'The new size is: %(bytes)d bytes (%(size)s).'
        ) % {'disk_name': self.disk.name, 'id': self.disk.id,
             'url': self.instance.get_absolute_url(),
             'vm_name': self.instance.name,
             'bytes': self.size, 'size': filesizeformat(self.size),
             }

    def is_acceptable(self):
        return self.instance.status in ResizeDiskOperation.accept_states


def send_notifications(sender, instance, created, **kwargs):
    if not created:
        return

    notification_msg = ugettext_noop(
        'A new <a href="%(request_url)s">%(request_type)s</a> was submitted '
        'by <a href="%(user_url)s">%(display_name)s</a>.')
    context = {
        'display_name': instance.user.profile.get_display_name(),
        'user_url': instance.user.profile.get_absolute_url(),
        'request_url': instance.get_absolute_url(),
        'request_type': u"%s" % instance.get_readable_type()
    }

    for u in User.objects.filter(is_superuser=True):
        u.profile.notify(
            ugettext_noop("New %(request_type)s"), notification_msg, context
        )

    instance.user.profile.notify(
        ugettext_noop("Request submitted"),
        ugettext_noop('You can view the request\'s status at this '
                      '<a href="%(request_url)s">link</a>.'), context
    )

    if settings.REQUEST_HOOK_URL:
        context.update({
            'object_kind': "request",
            'site_url': settings.DJANGO_URL,
        })
        try:
            r = requests.post(settings.REQUEST_HOOK_URL, timeout=3,
                              data=json.dumps(context, indent=2))
            r.raise_for_status()
        except requests.RequestException as e:
            logger.warning("Error in HTTP POST: %s. url: %s params: %s",
                           str(e), settings.REQUEST_HOOK_URL, context)
        else:
            logger.info("Successful HTTP POST. url: %s params: %s",
                        settings.REQUEST_HOOK_URL, context)


post_save.connect(send_notifications, sender=Request)
