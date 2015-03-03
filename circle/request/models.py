from django.db.models import (
    Model, CharField, IntegerField, TextField, ForeignKey, ManyToManyField,
)
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


class RequestType(Model):
    name = CharField(max_length=25)

    def __unicode__(self):
        return self.name


class Request(TimeStampedModel):
    STATUSES = Choices(
        ('UNSEEN', _("unseen")),
        ('PENDING', _('pending')),
        ('ACCEPTED', _('accepted')),
        ('DECLINED', _('declined')),
    )
    status = CharField(choices=STATUSES, default=STATUSES.UNSEEN,
                       max_length=10)
    user = ForeignKey(User, verbose_name=_('user'))
    TYPES = Choices(
        ('resource', _('resource request')),
        ('lease', _("lease request")),
        ('template', _("template access")),
    )
    type = CharField(choices=TYPES, max_length=10)
    reason = TextField(help_text="szia")
    action = ForeignKey(RequestAction)


class LeaseType(RequestType):
    lease = ForeignKey(Lease)

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

    def accept(self):
        pass
        # self.instance.change_resources(xy=xy)


class ExtendLeaseAction(RequestAction):
    instance = ForeignKey(Instance)
    lease_type = ForeignKey(LeaseType)

    def accept(self):
        pass


class TemplateAccessAction(RequestAction):
    template_type = ForeignKey(TemplateAccessType)
    LEVELS = Choices(
        ('user', _('user')),
        ('operator', _('operator')),
    )
    level = CharField(choices=LEVELS, default=LEVELS.user,
                      max_length=10)
    user = ForeignKey(User)

    def accept(self):
        pass
