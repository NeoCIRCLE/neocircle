from logging import getLogger

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.db.models import (
    Model, ForeignKey, OneToOneField, CharField, IntegerField
)
from django.utils.translation import ugettext_lazy as _

from vm.models import Instance

logger = getLogger(__name__)


class Favourite(Model):
    instance = ForeignKey(Instance)
    user = ForeignKey(User)


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
        return False

    pre_user_save.connect(save_org_id)

else:
    logger.debug("Do not register save_org_id to djangosaml2 pre_user_save")
