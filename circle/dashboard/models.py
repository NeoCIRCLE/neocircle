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

from __future__ import absolute_import

from itertools import chain
from hashlib import md5
from logging import getLogger

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.contrib.auth.signals import user_logged_in
from django.core.urlresolvers import reverse
from django.db.models import (
    Model, ForeignKey, OneToOneField, CharField, IntegerField, TextField,
    DateTimeField, permalink, BooleanField
)
from django.db.models.signals import post_save, pre_delete
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.utils.translation import ugettext_lazy as _, override, ugettext
from django_sshkey.models import UserKey

from model_utils.models import TimeStampedModel
from model_utils.fields import StatusField
from model_utils import Choices

from acl.models import AclBase

from vm.tasks.agent_tasks import add_keys, del_keys

logger = getLogger(__name__)


class Favourite(Model):
    instance = ForeignKey("vm.Instance")
    user = ForeignKey(User)


class Notification(TimeStampedModel):
    STATUS = Choices(('new', _('new')),
                     ('delivered', _('delivered')),
                     ('read', _('read')))

    status = StatusField()
    to = ForeignKey(User)
    subject = CharField(max_length=128)
    message = TextField()
    valid_until = DateTimeField(null=True, default=None)

    class Meta:
        ordering = ['-created']

    @classmethod
    def send(cls, user, subject, template, context={}, valid_until=None):
        try:
            language = user.profile.preferred_language
        except:
            language = None
        with override(language):
            context['user'] = user
            rendered = render_to_string(template, context)
            subject = ugettext(unicode(subject))
        return cls.objects.create(to=user, subject=subject, message=rendered,
                                  valid_until=valid_until)


class Profile(Model):
    user = OneToOneField(User)
    preferred_language = CharField(verbose_name=_('preferred language'),
                                   choices=settings.LANGUAGES,
                                   max_length=32,
                                   default=settings.LANGUAGE_CODE, blank=False)
    org_id = CharField(  # may be populated from eduPersonOrgId field
        unique=True, blank=True, null=True, max_length=64,
        help_text=_('Unique identifier of the person, e.g. a student number.'))
    instance_limit = IntegerField(default=5)
    use_gravatar = BooleanField(
        verbose_name=_("Use Gravatar"), default=True,
        help_text=_("Whether to use email address as Gravatar profile image"))
    email_notifications = BooleanField(
        verbose_name=_("Email notifications"), default=True,
        help_text=_('Whether user wants to get digested email notifications.'))

    def notify(self, subject, template, context={}, valid_until=None):
        return Notification.send(self.user, subject, template, context,
                                 valid_until)

    def get_absolute_url(self):
        return reverse("dashboard.views.profile",
                       kwargs={'username': self.user.username})

    def get_avatar_url(self):
        if self.use_gravatar:
            gravatar_hash = md5(self.user.email).hexdigest()
            return ("https://secure.gravatar.com/avatar/%s"
                    "?s=200" % gravatar_hash)
        else:
            return static("dashboard/img/avatar.png")

    def get_display_name(self):
        if self.user.get_full_name():
            name = self.user.get_full_name()
        else:
            name = self.user.username

        if self.org_id:
            name = "%s (%s)" % (name, self.org_id)
        return name

    def __unicode__(self):
        return self.get_display_name()


class FutureMember(Model):
    org_id = CharField(max_length=64, help_text=_(
        'Unique identifier of the person, e.g. a student number.'))
    group = ForeignKey(Group)

    class Meta:
        unique_together = ('org_id', 'group')


    def __unicode__(self):
        return u"%s (%s)" % (self.org_id, self.group)

class GroupProfile(AclBase):
    ACL_LEVELS = (
        ('operator', _('operator')),
        ('owner', _('owner')),
    )

    group = OneToOneField(Group)
    org_id = CharField(
        unique=True, blank=True, null=True, max_length=64,
        help_text=_('Unique identifier of the group at the organization.'))
    description = TextField(blank=True)

    def save(self, *args, **kwargs):
        if not self.org_id:
            self.org_id = None
        super(GroupProfile, self).save(*args, **kwargs)

    @classmethod
    def search(cls, name):
        try:
            return cls.objects.get(org_id=name).group
        except cls.DoesNotExist:
            return Group.objects.get(name=name)

    @permalink
    def get_absolute_url(self):
        return ('dashboard.views.group-detail', None,
                {'pk': self.group.pk})


def get_or_create_profile(self):
    obj, created = GroupProfile.objects.get_or_create(group_id=self.pk)
    return obj

Group.profile = property(get_or_create_profile)


def create_profile(sender, user, request, **kwargs):
    if not user.pk:
        return False
    profile, created = Profile.objects.get_or_create(user=user)
    return created

user_logged_in.connect(create_profile)

if hasattr(settings, 'SAML_ORG_ID_ATTRIBUTE'):
    logger.debug("Register save_org_id to djangosaml2 pre_user_save")
    from djangosaml2.signals import pre_user_save

    def save_org_id(sender, **kwargs):
        logger.debug("save_org_id called by %s", sender.username)
        attributes = kwargs.pop('attributes')
        atr = settings.SAML_ORG_ID_ATTRIBUTE
        try:
            value = attributes[atr][0]
        except Exception as e:
            value = None
            logger.info("save_org_id couldn't find attribute. %s", unicode(e))

        if sender.pk is None:
            sender.save()
            logger.debug("save_org_id saved user %s", unicode(sender))

        profile, created = Profile.objects.get_or_create(user=sender)
        if created or profile.org_id != value:
            logger.info("org_id of %s added to user %s's profile",
                        value, sender.username)
            profile.org_id = value
            profile.save()
        else:
            logger.debug("org_id of %s already added to user %s's profile",
                         value, sender.username)
        memberatrs = getattr(settings, 'SAML_GROUP_ATTRIBUTES', [])
        for group in chain(*[attributes[i]
                             for i in memberatrs if i in attributes]):
            try:
                g = GroupProfile.search(group)
            except Group.DoesNotExist:
                logger.debug('cant find membergroup %s', group)
            else:
                logger.debug('could find membergroup %s (%s)',
                             group, unicode(g))
                g.user_set.add(sender)

        for i in FutureMember.objects.filter(org_id=value):
            i.group.user_set.add(sender)
            i.delete()

        owneratrs = getattr(settings, 'SAML_GROUP_OWNER_ATTRIBUTES', [])
        for group in chain(*[attributes[i]
                             for i in owneratrs if i in attributes]):
            try:
                g = GroupProfile.search(group)
            except Group.DoesNotExist:
                logger.debug('cant find ownergroup %s', group)
            else:
                logger.debug('could find ownergroup %s (%s)',
                             group, unicode(g))
                g.profile.set_level(sender, 'owner')

        return False  # User did not change

    pre_user_save.connect(save_org_id)

else:
    logger.debug("Do not register save_org_id to djangosaml2 pre_user_save")


def add_ssh_keys(sender, **kwargs):
    from vm.models import Instance

    userkey = kwargs.get('instance')
    instances = Instance.get_objects_with_level(
        'user', userkey.user).filter(status='RUNNING')
    for i in instances:
        logger.info('called add_keys(%s, %s)', i, userkey)
        queue = i.get_remote_queue_name("agent")
        add_keys.apply_async(args=(i.vm_name, [userkey.key]),
                             queue=queue)


def del_ssh_keys(sender, **kwargs):
    from vm.models import Instance

    userkey = kwargs.get('instance')
    instances = Instance.get_objects_with_level(
        'user', userkey.user).filter(status='RUNNING')
    for i in instances:
        logger.info('called del_keys(%s, %s)', i, userkey)
        queue = i.get_remote_queue_name("agent")
        del_keys.apply_async(args=(i.vm_name, [userkey.key]),
                             queue=queue)


post_save.connect(add_ssh_keys, sender=UserKey)
pre_delete.connect(del_ssh_keys, sender=UserKey)
