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
    suspend_interval_seconds = IntegerField(
        verbose_name=_('suspend interval'), help_text=_(
            'Number of seconds after the an instance is suspended.'),
        null=True, blank=True)
    delete_interval_seconds = IntegerField(
        verbose_name=_('delete interval'), help_text=_(
            'Number of seconds after the an instance is deleted.'),
        null=True, blank=True)

    class Meta:
        app_label = 'vm'
        db_table = 'vm_lease'
        ordering = ['name', ]

    @property
    def suspend_interval(self):
        v = self.suspend_interval_seconds
        if v is not None:
            return timedelta(seconds=v)
        else:
            return None

    @suspend_interval.setter
    def suspend_interval(self, value):
        if value is not None:
            self.suspend_interval_seconds = value.total_seconds()
        else:
            self.suspend_interval_seconds = None

    @property
    def delete_interval(self):
        v = self.delete_interval_seconds
        if v is not None:
            return timedelta(seconds=v)
        else:
            return None

    @delete_interval.setter
    def delete_interval(self, value):
        if value is not None:
            self.delete_interval_seconds = value.total_seconds()
        else:
            self.delete_interval_seconds = None

    def get_readable_suspend_time(self):
        v = self.suspend_interval
        if v is not None:
            n = datetime.utcnow()
            return timeuntil(n + v, n)
        else:
            return _("never")

    def get_readable_delete_time(self):
        v = self.delete_interval
        if v is not None:
            n = datetime.utcnow()
            return timeuntil(n + v, n)
        else:
            return _("never")

    def __unicode__(self):
        return _("%(name)s (suspend: %(s)s, remove: %(r)s)") % {
            'name': self.name,
            's': self.get_readable_suspend_time(),
            'r': self.get_readable_delete_time()}


class Trait(Model):
    name = CharField(max_length=50, verbose_name=_('name'))

    class Meta:
        app_label = 'vm'
        db_table = 'vm_trait'

    def __unicode__(self):
        return self.name
