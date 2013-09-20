# coding=utf-8

import logging
import uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from sizefield.models import FileSizeField

from .tasks import local_tasks, remote_tasks

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
    name = models.CharField(blank=True, max_length=100,
                            verbose_name=_('name'))
    filename = models.CharField(max_length=256, verbose_name=_('filename'))
    datastore = models.ForeignKey(DataStore)
    type = models.CharField(max_length=10, choices=TYPES)
    size = FileSizeField()
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

    class WrongDiskTypeError(Exception):
        def __init__(self, type):
            self.type = type

        def __str__(self):
            return ("Operation can't be invoked on a disk of type '%s'." %
                    self.type)

    def get_exclusive(self):
        """Get an instance of the disk for exclusive usage.
        """
        if self.type in ['qcow2-snap', 'raw-rw']:
            raise self.WrongDiskTypeError(self.type)

        filename = self.filename if self.type == 'iso' else str(uuid.uuid4())
        new_type = {
            'qcow2-norm': 'qcow2-snap',
            'iso': 'iso',
            'raw-ro': 'raw-rw',
        }[self.type]

        return Disk(base=self, datastore=self.datastore, filename=filename,
                    name=self.name, size=self.size, type=new_type)

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
        local_tasks.deploy.apply_async(self)

    def deploy(self):
        """Reify the disk model on the associated data store.

        :param self: the disk model to reify
        :type self: storage.models.Disk

        :return: True if a new reification of the disk has been created;
                 otherwise, False.
        :rtype: bool
        """
        if self.ready:
            return False

        disk_desc = {
            'name': self.filename,
            'dir': self.datastore.path,
            'format': self.format,
            'size': self.size,
            'base_name': self.base.name if self.base else None,
            'type': 'snapshot' if self.type == 'qcow2-snap' else 'normal'
        }
        remote_tasks.create_disk.apply_async(
            args=[disk_desc], queue=self.datastore.hostname + ".storage").get()
        self.ready = True
        self.save()
        return True

    def delete(self):
        # TODO
        # StorageDriver.delete_disk.delay(instance.to_json()).get()
        pass
