from __future__ import absolute_import, unicode_literals
from datetime import timedelta, datetime

from django.db.models import Model, CharField, IntegerField
from django.utils.translation import ugettext_lazy as _
from django.utils.timesince import timeuntil

from model_utils.models import TimeStampedModel


ARCHITECTURES = (('x86_64', 'x86-64 (64 bit)'),
                 ('i686', 'x86 (32 bit)'))


class BaseResourceConfigModel(Model):

    """Abstract base for models with base resource configuration parameters.
    """
    num_cores = IntegerField(verbose_name=_('number of cores'),
                             help_text=_('Number of virtual CPU cores '
                                         'available to the virtual machine.'))
    ram_size = IntegerField(verbose_name=_('RAM size'),
                            help_text=_('Mebibytes of memory.'))
    max_ram_size = IntegerField(verbose_name=_('maximal RAM size'),
                                help_text=_('Upper memory size limit '
                                            'for balloning.'))
    arch = CharField(max_length=10, verbose_name=_('architecture'),
                     choices=ARCHITECTURES)
    priority = IntegerField(verbose_name=_('priority'),
                            help_text=_('CPU priority.'))

    class Meta:
        abstract = True


class NamedBaseResourceConfig(BaseResourceConfigModel, TimeStampedModel):

    """Pre-created, named base resource configurations.
    """
    name = CharField(max_length=50, unique=True,
                     verbose_name=_('name'), help_text=
                     _('Name of base resource configuration.'))

    class Meta:
        app_label = 'vm'
        db_table = 'vm_namedbaseresourceconfig'

    def __unicode__(self):
        return self.name


class Lease(Model):

    """Lease times for VM instances.

    Specifies a time duration until suspension and deletion of a VM
    instance.
    """
    name = CharField(max_length=100, unique=True,
                     verbose_name=_('name'))
    suspend_interval_seconds = IntegerField(verbose_name=_('suspend interval'))
    delete_interval_seconds = IntegerField(verbose_name=_('delete interval'))

    class Meta:
        app_label = 'vm'
        db_table = 'vm_lease'
        ordering = ['name', ]

    @property
    def suspend_interval(self):
        return timedelta(seconds=self.suspend_interval_seconds)

    @suspend_interval.setter
    def suspend_interval(self, value):
        self.suspend_interval_seconds = value.seconds

    @property
    def delete_interval(self):
        return timedelta(seconds=self.delete_interval_seconds)

    @delete_interval.setter
    def delete_interval(self, value):
        self.delete_interval_seconds = value.seconds

    def get_readable_suspend_time(self):
        return timeuntil(datetime.utcnow() + self.suspend_interval,
                         datetime.utcnow())

    def get_readable_delete_time(self):
        return timeuntil(datetime.utcnow() + self.delete_interval,
                         datetime.utcnow())

    def __unicode__(self):
        return "%s (%s) - (%s)" % (self.name,
                                   self.get_readable_suspend_time(),
                                   self.get_readable_delete_time())


class Trait(Model):
    name = CharField(max_length=50, verbose_name=_('name'))

    class Meta:
        app_label = 'vm'
        db_table = 'vm_trait'

    def __unicode__(self):
        return self.name
