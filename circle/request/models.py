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
from django.db.models import (
    Model, CharField, IntegerField, TextField, ForeignKey, ManyToManyField,
)
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

from model_utils.models import TimeStampedModel
from model_utils import Choices

from vm.models import Instance, InstanceTemplate, Lease


class RequestAction(Model):

    def accept(self):
        raise NotImplementedError

    class Meta:
        abstract = True


class RequestType(Model):
    name = CharField(max_length=25)

    def __unicode__(self):
        return self.name

    class Meta:
        abstract = True


class Request(TimeStampedModel):
    STATUSES = Choices(
        ('UNSEEN', _("unseen")),
        ('PENDING', _('pending')),
        ('ACCEPTED', _('accepted')),
        ('DECLINED', _('declined')),
    )
    status = CharField(choices=STATUSES, default=STATUSES.UNSEEN,
                       max_length=10)
    user = ForeignKey(User, related_name="user")
    closed_by = ForeignKey(User, related_name="closed_by", null=True)
    TYPES = Choices(
        ('resource', _('resource request')),
        ('lease', _("lease request")),
        ('template', _("template access")),
    )
    type = CharField(choices=TYPES, max_length=10)
    reason = TextField(help_text="szia")

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
            'template': "puzzle-piece"
        }.get(self.type)

    def get_effect(self):
        return {
            "UNSEEN": "primary",
            "PENDING": "warning",
            "ACCEPTED": "success",
            "DECLINED": "danger",
        }.get(self.status)

    def get_status_icon(self):
        return {
            "UNSEEN": "eye-slash",
            "PENDING": "exclamation-triangle",
            "ACCEPTED": "check",
            "DECLINED": "times",
        }.get(self.status)

    def accept(self, user):
        self.action.accept(user)
        self.status = "ACCEPTED"
        self.closed_by = user
        self.save()

    def decline(self, user):
        self.status = "DECLINED"
        self.closed_by = user
        self.save()


class LeaseType(RequestType):
    lease = ForeignKey(Lease)

    def __unicode__(self):
        return _("%(name)s (suspend: %(s)s, remove: %(r)s)") % {
            'name': self.name,
            's': self.lease.get_readable_suspend_time(),
            'r': self.lease.get_readable_delete_time()}

    def get_absolute_url(self):
        return reverse("request.views.lease-type-detail",
                       kwargs={'pk': self.pk})


class TemplateAccessType(RequestType):
    templates = ManyToManyField(InstanceTemplate)

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
        self.instance.resources_request.async(user=user, resource_request=self)


class ExtendLeaseAction(RequestAction):
    instance = ForeignKey(Instance)
    lease_type = ForeignKey(LeaseType)

    def accept(self, user):
        self.instance.renew(lease=self.lease_type.lease, save=True, force=True,
                            user=user)


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
