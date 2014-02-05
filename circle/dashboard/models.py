from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Model, ForeignKey, OneToOneField, CharField
from django.utils.translation import ugettext_lazy as _

from vm.models import Instance


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
