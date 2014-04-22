from itertools import chain
from logging import getLogger

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.contrib.auth.signals import user_logged_in
from django.core.urlresolvers import reverse
from django.db.models import (
    Model, ForeignKey, OneToOneField, CharField, IntegerField, TextField,
    DateTimeField,
)
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _, override, ugettext

from model_utils.models import TimeStampedModel
from model_utils.fields import StatusField
from model_utils import Choices

from acl.models import AclBase

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

    def notify(self, subject, template, context={}, valid_until=None):
        return Notification.send(self.user, subject, template, context,
                                 valid_until)

    def get_absolute_url(self):
        return reverse("dashboard.views.profile")


class GroupProfile(AclBase):
    ACL_LEVELS = (
        ('operator', _('operator')),
        ('owner', _('owner')),
    )

    group = OneToOneField(Group)
    org_id = CharField(
        unique=True, blank=True, null=True, max_length=64,
        help_text=_('Unique identifier of the group at the organization.'))
    description = TextField()

    @classmethod
    def search(cls, name):
        try:
            return cls.objects.get(org_id=name).group
        except cls.DoesNotExist:
            return Group.objects.get(name=name)


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
        for group in chain(*[attributes[i] for i in memberatrs]):
            try:
                g = GroupProfile.search(group)
            except Group.DoesNotExist:
                logger.debug('cant find membergroup %s', group)
            else:
                logger.debug('could find membergroup %s (%s)',
                             group, unicode(g))
                g.user_set.add(sender)

        owneratrs = getattr(settings, 'SAML_GROUP_OWNER_ATTRIBUTES', [])
        for group in chain(*[attributes[i] for i in owneratrs]):
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
