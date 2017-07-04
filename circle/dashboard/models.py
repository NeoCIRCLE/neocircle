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

from datetime import timedelta
from itertools import chain
from hashlib import md5
from logging import getLogger

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.contrib.auth.signals import user_logged_in
from django.core.urlresolvers import reverse
from django.db.models import (
    Model, ForeignKey, OneToOneField, CharField, IntegerField, TextField,
    DateTimeField, BooleanField
)
from django.db.models.signals import post_save, pre_delete, post_delete
from django.templatetags.static import static
from django.utils import timezone
from django.utils.html import escape
from django.utils.translation import ugettext_lazy as _
from django_sshkey.models import UserKey
from django.core.exceptions import ObjectDoesNotExist

from sizefield.models import FileSizeField

from jsonfield import JSONField
from model_utils.models import TimeFramedModel, TimeStampedModel
from model_utils.fields import StatusField
from model_utils import Choices

from acl.models import AclBase
from common.models import HumanReadableObject, create_readable, Encoder

from vm.models.instance import ACCESS_METHODS

from .store_api import Store, NoStoreException, NotOkException, Timeout
from .validators import connect_command_template_validator

logger = getLogger(__name__)


def pwgen():
    return User.objects.make_random_password()


class Message(TimeStampedModel, TimeFramedModel):
    message = CharField(max_length=500, verbose_name=_('message'))
    effect = CharField(
        default='info', max_length=10, verbose_name=_('effect'),
        choices=(('success', _('success')), ('info', _('info')),
                 ('warning', _('warning')), ('danger', _('danger'))))
    enabled = BooleanField(default=False, verbose_name=_('enabled'))

    class Meta:
        ordering = ["id"]
        verbose_name = _('message')
        verbose_name_plural = _('messages')

    def __unicode__(self):
        return self.message

    def get_absolute_url(self):
        return reverse('dashboard.views.message-detail',
                       kwargs={'pk': self.pk})


class Favourite(Model):
    instance = ForeignKey("vm.Instance")
    user = ForeignKey(User)


class Notification(TimeStampedModel):
    STATUS = Choices(('new', _('new')),
                     ('delivered', _('delivered')),
                     ('read', _('read')))

    status = StatusField()
    to = ForeignKey(User)
    subject_data = JSONField(null=True, dump_kwargs={"cls": Encoder})
    message_data = JSONField(null=True, dump_kwargs={"cls": Encoder})
    valid_until = DateTimeField(null=True, default=None)

    class Meta:
        ordering = ['-created']

    @classmethod
    def send(cls, user, subject, template, context,
             valid_until=None, subject_context=None):
        hro = create_readable(template, user=user, **context)
        subject = create_readable(subject, **(subject_context or context))
        return cls.objects.create(to=user,
                                  subject_data=subject.to_dict(),
                                  message_data=hro.to_dict(),
                                  valid_until=valid_until)

    @property
    def subject(self):
        return HumanReadableObject.from_dict(
            self.escape_dict(self.subject_data))

    @subject.setter
    def subject(self, value):
        self.subject_data = None if value is None else value.to_dict()

    @property
    def message(self):
        return HumanReadableObject.from_dict(
            self.escape_dict(self.message_data))

    def escape_dict(self, data):
        for k, v in data['params'].items():
            if isinstance(v, basestring):
                data['params'][k] = escape(v)
        return data

    @message.setter
    def message(self, value):
        self.message_data = None if value is None else value.to_dict()

    @property
    def has_valid_renew_url(self):
        params = self.message_data['params']
        return ('token' in params and 'suspend' in params and
                self.modified > timezone.now() - timedelta(days=3))

    @property
    def renew_url(self):
        return (settings.DJANGO_URL.rstrip("/") +
                str(self.message_data['params'].get('token')))


class ConnectCommand(Model):
    user = ForeignKey(User, related_name='command_set')
    access_method = CharField(max_length=10, choices=ACCESS_METHODS,
                              verbose_name=_('access method'),
                              help_text=_('Type of the remote access method.'))
    name = CharField(max_length=128, verbose_name=_('name'), blank=False,
                     help_text=_("Name of your custom command."))
    template = CharField(blank=True, null=True, max_length=256,
                         verbose_name=_('command template'),
                         help_text=_('Template for connection command string. '
                                     'Available parameters are: '
                                     'username, password, '
                                     'host, port.'),
                         validators=[connect_command_template_validator])

    class Meta:
        ordering = ('id', )

    def __unicode__(self):
        return self.template


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
    desktop_notifications = BooleanField(
        verbose_name=_("Desktop notifications"), default=False,
        help_text=_('Whether user wants to get desktop notification when an '
                    'activity has finished and the window is not in focus.'))
    smb_password = CharField(
        max_length=20,
        verbose_name=_('Samba password'),
        help_text=_(
            'Generated password for accessing store from '
            'virtual machines.'),
        default=pwgen,
    )
    disk_quota = FileSizeField(
        verbose_name=_('disk quota'),
        default=2048 * 1024 * 1024,
        help_text=_('Disk quota in mebibytes.'))
    two_factor_secret = CharField(
        verbose_name=_("two factor secret key"),
        max_length=32, null=True, blank=True,
    )

    def get_connect_commands(self, instance, use_ipv6=False):
        """ Generate connection command based on template."""
        single_command = instance.get_connect_command(use_ipv6)
        if single_command:  # can we even connect to that VM
            commands = self.user.command_set.filter(
                access_method=instance.access_method)
            if commands.count() < 1:
                return [single_command]
            else:
                return [
                    command.template % {
                        'port': instance.get_connect_port(use_ipv6=use_ipv6),
                        'host':  instance.get_connect_host(use_ipv6=use_ipv6),
                        'password': instance.pw,
                        'username': 'cloud',
                    } for command in commands]
        else:
            return []

    def notify(self, subject, template, context=None, valid_until=None,
               **kwargs):
        if context is not None:
            kwargs.update(context)
        return Notification.send(self.user, subject, template, kwargs,
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

    def save(self, *args, **kwargs):
        if self.org_id == "":
            self.org_id = None
        super(Profile, self).save(*args, **kwargs)

    class Meta:
        ordering = ('id', )
        permissions = (
            ('use_autocomplete', _('Can use autocomplete.')),
        )


class FutureMember(Model):
    org_id = CharField(max_length=64, help_text=_(
        'Unique identifier of the person, e.g. a student number.'))
    group = ForeignKey(Group)

    class Meta:
        ordering = ('id', )
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

    class Meta:
        ordering = ('id', )

    def __unicode__(self):
        return self.group.name

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

    def get_absolute_url(self):
        return reverse('dashboard.views.group-detail',
                       kwargs={'pk': self.group.pk})


def get_or_create_profile(self):
    obj, created = GroupProfile.objects.get_or_create(group_id=self.pk)
    return obj

Group.profile = property(get_or_create_profile)


def create_profile(user):
    if not user.pk:
        return False
    profile, created = Profile.objects.get_or_create(user=user)

    try:
        Store(user).create_user(profile.smb_password, None, profile.disk_quota)
    except:
        logger.exception("Can't create user %s", unicode(user))
    return created


def create_profile_hook(sender, user, request, **kwargs):
    return create_profile(user)

user_logged_in.connect(create_profile_hook)

if hasattr(settings, 'SAML_ORG_ID_ATTRIBUTE'):
    logger.debug("Register save_org_id to djangosaml2 pre_user_save")
    from djangosaml2.signals import pre_user_save

    def save_org_id(sender, **kwargs):
        logger.debug("save_org_id called by %s", sender.username)
        attributes = kwargs.pop('attributes')
        atr = settings.SAML_ORG_ID_ATTRIBUTE
        try:
            value = attributes[atr][0].upper()
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

        for i in FutureMember.objects.filter(org_id__iexact=value):
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


def update_store_profile(sender, **kwargs):
    profile = kwargs.get('instance')
    keys = [i.key for i in profile.user.userkey_set.all()]
    try:
        s = Store(profile.user)
        s.create_user(profile.smb_password, keys,
                      profile.disk_quota)
    except NoStoreException:
        logger.debug("Store is not available.")
    except (NotOkException, Timeout):
        logger.critical("Store is not accepting connections.")


post_save.connect(update_store_profile, sender=Profile)


def update_store_keys(sender, **kwargs):
    userkey = kwargs.get('instance')
    try:
        profile = userkey.user.profile
    except ObjectDoesNotExist:
        pass  # If there is no profile the user is deleted
    else:
        keys = [i.key for i in profile.user.userkey_set.all()]
        try:
            s = Store(userkey.user)
            s.create_user(profile.smb_password, keys,
                          profile.disk_quota)
        except NoStoreException:
            logger.debug("Store is not available.")
        except NotOkException:
            logger.critical("Store is not accepting connections.")


post_save.connect(update_store_keys, sender=UserKey)
post_delete.connect(update_store_keys, sender=UserKey)


def add_ssh_keys(sender, **kwargs):
    from vm.models import Instance

    userkey = kwargs.get('instance')
    instances = Instance.get_objects_with_level(
        'user', userkey.user, disregard_superuser=True
    ).filter(status='RUNNING')
    for i in instances:
        logger.info('called add_keys(%s, %s)', i, userkey)
        try:
            i.install_keys(user=userkey.user, keys=[userkey.key])
        except Instance.NoAgentError:
            logger.info("%s has no agent running", i)


def del_ssh_keys(sender, **kwargs):
    from vm.models import Instance

    userkey = kwargs.get('instance')
    instances = Instance.get_objects_with_level(
        'user', userkey.user, disregard_superuser=True
    ).filter(status='RUNNING')
    for i in instances:
        logger.info('called del_keys(%s, %s)', i, userkey)
        try:
            i.remove_keys(user=userkey.user, keys=[userkey.key])
        except Instance.NoAgentError:
            logger.info("%s has no agent running", i)


post_save.connect(add_ssh_keys, sender=UserKey)
pre_delete.connect(del_ssh_keys, sender=UserKey)
