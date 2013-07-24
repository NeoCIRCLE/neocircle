# coding=utf-8

import logging
import jsonpickle
import json
from django.db import models, transaction
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_save, post_delete

from .tasks import StorageDriver

logger = logging.getLogger(__name__)


class DataStore(models.Model):
    name = models.CharField(max_length=100, unique=True,
                            verbose_name=_('name'))
    path = models.CharField(max_length=200, unique=True,
                            verbose_name=_('path'))

    class Meta:
        ordering = ['name']
        verbose_name = _('datastore')
        verbose_name_plural = _('datastores')

    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.path)


class Disk(models.Model):
    """Virtual disks automatically synchronized with OpenNebula."""
    name = models.CharField(max_length=100, unique=True,
                            verbose_name=_('name'))
    datastore = models.ForeignKey('DataStore')
    format = models.CharField(max_length=10,
                              choices=(('qcow2', 'qcow2'), ('raw', 'raw')))
    size = models.IntegerField()
    type = models.CharField(max_length=10,
                            choices=(('snapshot', 'snapshot'),
                                     ('normal', 'normal')))
    base = models.ForeignKey('Disk', related_name='snapshots',
                             null=True, blank=True)
    original_parent = models.ForeignKey('Disk', null=True, blank=True)
    created = models.BooleanField(default=False)

    class Meta:
        ordering = ['name']
        verbose_name = _('disk')
        verbose_name_plural = _('disks')

    def to_json(self):
        self.base_name = self.base.name if self.base else None
        self.dir = self.datastore.path
        return jsonpickle.encode(self, unpicklable=True)

    def __unicode__(self):
        return u"%s (#%d)" % (self.name, self.id)

    @classmethod
    def create_signal(cls, sender, instance, created, **kwargs):
        if not instance.created:
            StorageDriver.create_disk.delay(instance.to_json()).get()
            instance.created = True
            instance.save()

    @classmethod
    def delete_signal(cls, sender, instance, using, **kwargs):
        StorageDriver.delete_disk.delay(instance.to_json()).get()

    @classmethod
    def update_disk(cls, disk):
        name = disk['name']
        modified = False
        try:
            base = cls.objects.get(name=disk['base_name'])
        except cls.DoesNotExist:
            base = None

        try:
            d = cls.objects.get(name=name)
        except Disk.DoesNotExist:
            d = Disk(name=name,
                     created=True,
                     datastore=DataStore.objects.get(path=disk['dir']),
                     format=disk['format'],
                     type=disk['type'])
            modified = True

        if d.size != disk['size'] or d.base != base:
            d.size = disk['size']
            d.base = base
            modified = True

        if modified:
            d.full_clean()
            d.save()

    @classmethod
    def update_disks(cls, delete=True):
        """Get and register virtual disks from OpenNebula."""
        try:
            json_data = StorageDriver.list_disks.delay().get(timeout=10)
            disks = json.loads(json_data)
        except:
            return
        with transaction.commit_on_success():
            l = []
            for disk in disks:
                print disk
                cls.update_disk(disk)
                l.append(disk['name'])
            if delete:
                cls.objects.exclude(name__in=l).delete()

post_save.connect(Disk.create_signal, sender=Disk)
post_delete.connect(Disk.delete_signal, sender=Disk)
