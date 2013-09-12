# coding=utf-8

import logging
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_delete
from model_utils.models import TimeStampedModel

import manager.storage

from . import tasks

logger = logging.getLogger(__name__)


class DataStore(models.Model):

    """Collection of virtual disks.
    """
    name = models.CharField(max_length=100, unique=True,
                            verbose_name=_('name'))
    path = models.CharField(max_length=200, unique=True,
                            verbose_name=_('path'))
    hostname = models.CharField(max_length=40, unique=True,
                                verbose_name=_('hostname'))

    class Meta:
        ordering = ['name']
        verbose_name = _('datastore')
        verbose_name_plural = _('datastores')

    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.path)


class Disk(TimeStampedModel):

    """A virtual disk.
    """
    TYPES = [('qcow2-norm', 'qcow2 normal'), ('qcow2-snap', 'qcow2 snapshot'),
             ('iso', 'iso'), ('raw-ro', 'raw read-only'), ('raw-rw', 'raw')]
    name = models.CharField(max_length=100, verbose_name=_('name'))
    filename = models.CharField(max_length=256, unique=True,
                                verbose_name=_('filename'))
    datastore = models.ForeignKey(DataStore)
    type = models.CharField(max_length=10, choices=TYPES)
    size = models.IntegerField()
    base = models.ForeignKey('self', blank=True, null=True,
                             related_name='derivatives')
    ready = models.BooleanField(default=False)
    dev_num = models.CharField(default='a', max_length=1,
                               verbose_name="device number")

    class Meta:
        ordering = ['name']
        verbose_name = _('disk')
        verbose_name_plural = _('disks')

    @property
    def path(self):
        return self.datastore.path + '/' + self.filename

    @property
    def format(self):
        return {
            'qcow2-norm': 'qcow2',
            'qcow2-snap': 'qcow2',
            'iso': 'iso',
            'raw-ro': 'raw',
            'raw-rw': 'raw',
        }[self.type]

    def get_exclusive(self):
        """Get an instance of the disk for exclusive usage.

        It might mean copying the disk, creating a snapshot or creating a
        symbolic link to a read-only image.
        """
        # TODO implement (or call) logic
        return self

    @property
    def device_type(self):
        return {
            'qcow2': 'vd',
            'raw': 'vd',
            'iso': 'hd',
        }[self.format]

    def get_vmdisk_desc(self):
        return {
            'source': self.path,
            'driver_type': self.format,
            'driver_cache': 'default',
            'target_device': self.device_type + self.dev_num
        }

    def __unicode__(self):
        return u"%s (#%d)" % (self.name, self.id)

    def deploy_async(self):
        manager.storage.deploy.apply_async(self)

    def deploy(self):
        if self.ready:
            return

        disk_desc = {
            'name': self.name,
            'dir': self.datastore.path,
            'format': self.format,
            'size': self.size,
            'base_name': self.base.name if self.base else None,
            'type': self.type
        }
        tasks.create_disk.delay(disk_desc).get()
        self.ready = True
        self.save()

    @classmethod
    def delete_signal(cls, sender, instance, using, **kwargs):
        # TODO
        # StorageDriver.delete_disk.delay(instance.to_json()).get()
        pass

post_delete.connect(Disk.delete_signal, sender=Disk)
