# coding=utf-8

import logging
import uuid

from django.contrib.auth.models import User
from django.db.models import (Model, BooleanField, CharField, DateTimeField,
                              ForeignKey, TextField)
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from sizefield.models import FileSizeField

from .tasks import local_tasks, remote_tasks

logger = logging.getLogger(__name__)


class DataStore(Model):

    """Collection of virtual disks.
    """
    name = CharField(max_length=100, unique=True, verbose_name=_('name'))
    path = CharField(max_length=200, unique=True, verbose_name=_('path'))
    hostname = CharField(max_length=40, unique=True,
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
    name = CharField(blank=True, max_length=100, verbose_name=_("name"))
    filename = CharField(max_length=256, verbose_name=_("filename"))
    datastore = ForeignKey(DataStore, verbose_name=_("datastore"),
                           help_text=_("The datastore that holds the disk."))
    type = CharField(max_length=10, choices=TYPES)
    size = FileSizeField()
    base = ForeignKey('self', blank=True, null=True,
                      related_name='derivatives')
    ready = BooleanField(default=False)
    dev_num = CharField(default='a', max_length=1,
                        verbose_name=_("device number"))

    class Meta:
        ordering = ['name']
        verbose_name = _('disk')
        verbose_name_plural = _('disks')

    class WrongDiskTypeError(Exception):
        def __init__(self, type):
            self.type = type

        def __str__(self):
            return ("Operation can't be invoked on a disk of type '%s'." %
                    self.type)

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

    @property
    def device_type(self):
        return {
            'qcow2': 'vd',
            'raw': 'vd',
            'iso': 'hd',
        }[self.format]

    def get_exclusive(self):
        """Get an instance of the disk for exclusive usage.

        This method manipulates the database only.
        """
        type_mapping = {
            'qcow2-norm': 'qcow2-snap',
            'iso': 'iso',
            'raw-ro': 'raw-rw',
        }

        if self.type not in type_mapping.keys():
            raise self.WrongDiskTypeError(self.type)

        filename = self.filename if self.type == 'iso' else str(uuid.uuid4())
        new_type = type_mapping[self.type]

        return Disk.objects.create(base=self, datastore=self.datastore,
                                   filename=filename, name=self.name,
                                   size=self.size, type=new_type)

    def get_vmdisk_desc(self):
        return {
            'source': self.path,
            'driver_type': self.format,
            'driver_cache': 'default',
            'target_device': self.device_type + self.dev_num
        }

    def get_disk_desc(self):
        return {
            'name': self.filename,
            'dir': self.datastore.path,
            'format': self.format,
            'size': self.size,
            'base_name': self.base.filename if self.base else None,
            'type': 'snapshot' if self.type == 'qcow2-snap' else 'normal'
        }

    def __unicode__(self):
        return u"%s (#%d)" % (self.name, self.id)

    def clean(self, *args, **kwargs):
        if self.size == "" and self.base:
            self.size = self.base.size
        super(Disk, self).clean(*args, **kwargs)

    def deploy(self, user=None, task_uuid=None):
        """Reify the disk model on the associated data store.

        :param self: the disk model to reify
        :type self: storage.models.Disk

        :return: True if a new reification of the disk has been created;
                 otherwise, False.
        :rtype: bool
        """
        if self.ready:
            return False

        # Delegate create / snapshot jobs
        disk_desc = self.get_disk_desc()
        if self.type == 'qcow2-snap':
            remote_tasks.snapshot.apply_async(
                args=[disk_desc],
                queue=self.datastore.hostname + ".storage").get()
        else:
            remote_tasks.create.apply_async(
                args=[disk_desc],
                queue=self.datastore.hostname + ".storage").get()

        self.ready = True
        self.save()
        return True

    def deploy_async(self, user=None):
        """Execute deploy asynchronously.
        """
        local_tasks.deploy.apply_async(args=[self, user],
                                       queue="localhost.man")

    def delete(self):
        # TODO
        # StorageDriver.delete_disk.delay(instance.to_json()).get()
        pass


class DiskActivity(TimeStampedModel):
    activity_code = CharField(verbose_name=_('activity_code'), max_length=100)
    task_uuid = CharField(verbose_name=_('task_uuid'), blank=True,
                          max_length=50, null=True, unique=True)
    disk = ForeignKey(Disk, verbose_name=_('disk'),
                      related_name='activity_log')
    user = ForeignKey(User, verbose_name=_('user'), blank=True, null=True)
    started = DateTimeField(verbose_name=_('started'), blank=True, null=True)
    finished = DateTimeField(verbose_name=_('finished'), blank=True, null=True)
    result = TextField(verbose_name=_('result'), blank=True, null=True)
    state = CharField(verbose_name=_('state'), default='PENDING',
                      max_length=50)

    def update_state(self, new_state):
        self.state = new_state
        self.save()

    def finish(self, result=None):
        if not self.finished:
            self.finished = timezone.now()
            self.result = result
            self.state = 'COMPLETED'
            self.save()
