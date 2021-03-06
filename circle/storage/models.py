# -*- coding: utf-8 -*-

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

from __future__ import unicode_literals

import logging
from os.path import join
import uuid
import re

from django.conf import settings
from celery.contrib.abortable import AbortableAsyncResult
from django.db.models import (Model, BooleanField, CharField, DateTimeField,
                              ForeignKey)
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _, ugettext_noop
from model_utils.models import TimeStampedModel
from sizefield.models import FileSizeField

from .tasks import local_tasks, storage_tasks
from celery.exceptions import TimeoutError
from common.models import (
    WorkerNotFound, HumanReadableException, humanize_exception, method_cache
)

logger = logging.getLogger(__name__)


def validate_ascii(value):

    try:
        str(value)
    except UnicodeEncodeError:
        raise ValidationError("%s is not 'ascii' string" % value)


class DataStore(Model):

    """Collection of virtual disks.
    """
    TYPES = (('file', 'filesystem'), ('ceph_block', 'Ceph block device'))

    type = CharField(max_length=10, verbose_name=_('type'),
                     default='file', choices=TYPES)
    name = CharField(max_length=100, unique=True, verbose_name=_('name'))
    # path or pool name when use ceph block device storage
    path = CharField(max_length=200, unique=True,
                     verbose_name=_('path or poolname'),
                     validators=[validate_ascii])
    # hostname of storage driver
    hostname = CharField(max_length=40, verbose_name=_('hostname'))

    ceph_user = CharField(max_length=255, null=True, blank=True,
                          verbose_name=_('Ceph username'))
    destroyed = DateTimeField(blank=True, default=None, null=True)

    ceph_user_changed = False

    class Meta:
        ordering = ['name']
        verbose_name = _('datastore')
        verbose_name_plural = _('datastores')

    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.path)

    def save(self, *args, **kwargs):
        if self.pk is not None:
            orig = DataStore.objects.get(pk=self.pk)
            self.ceph_user_changed = orig.ceph_user != self.ceph_user
        super(DataStore, self).save(*args, **kwargs)

    def get_remote_queue_name(self, queue_id, priority=None,
                              check_worker=True):
        logger.debug("Checking for storage queue %s.%s",
                     self.hostname, queue_id)
        if not check_worker or local_tasks.check_queue(self.hostname,
                                                       queue_id,
                                                       priority):
            queue_name = self.hostname + '.' + queue_id
            if priority is not None:
                queue_name = queue_name + '.' + priority
            return queue_name
        else:
            raise WorkerNotFound()

    def get_deletable_disks(self):
        deletables = [disk for disk in self.disk_set.filter(
                      destroyed__isnull=False) if disk.is_deletable]
        deletables = sorted(deletables, key=lambda disk: disk.destroyed)

        return [disk.filename for disk in deletables]

    def destroy(self):
        if self.destroyed:
            return False

        self.destroyed = timezone.now()
        self.save()
        return True

    @property
    def used_percent(self):
        try:
            stats = self.get_statistics()
        except WorkerNotFound:
            return -1  # invalid value for unreachable
        free_percent = float(stats['free_percent'])
        return int(100 - free_percent)

    @property
    def is_destroyable(self):
        disk_count = self.disk_set.filter(destroyed__isnull=True).count()
        template_count = self.instancetemplate_set.count()
        vm_count = self.instance_set.filter(destroyed_at__isnull=True).count()
        return 0 == disk_count + vm_count + template_count

    @method_cache(30)
    def get_statistics(self, timeout=15):
        q = self.get_remote_queue_name("storage", priority="fast")
        try:
            return storage_tasks.get_storage_stat.apply_async(
                args=[self.type, self.path], queue=q).get(timeout=timeout)
        except Exception:
            return {'free_space': -1,
                    'free_percent': -1}

    @method_cache(30)
    def get_orphan_disks(self, timeout=15):
        """Disk image files without Disk object in the database.

        Exclude cloud-xxxxxxxx.dump format images.

        :param timeout: Seconds before TimeOut exception
        :type timeout: int
        """
        queue_name = self.get_remote_queue_name('storage', "slow")
        files = set(storage_tasks.list_files.apply_async(
            args=[self.type, self.path], queue=queue_name).get(
                timeout=timeout))
        disks = set([disk.filename for disk in self.disk_set.all()])

        orphans = []
        for i in files - disks:
            if not re.match('cloud-[0-9]*\.dump', i):
                orphans.append(i)
        return orphans

    @method_cache(30)
    def get_missing_disks(self, timeout=15):
        """Disk objects without disk image files.

        :param timeout: Seconds before TimeOut exception
        :type timeout: int
        """
        queue_name = self.get_remote_queue_name('storage', "slow")
        files = set(storage_tasks.list_files.apply_async(
            args=[self.type, self.path], queue=queue_name).get(
                timeout=timeout))
        disks = Disk.objects.filter(destroyed__isnull=True, is_ready=True,
                                    datastore=self)
        return disks.exclude(filename__in=files)

    @classmethod
    def get_default_datastore(cls):
        try:
            datastore_name = settings.DEFAULT_DATASTORE
            if datastore_name:
                return cls.objects.get(name=datastore_name)
        except cls.DoesNotExist:
            pass
        return cls.objects.all()[0]  # TODO

    @classmethod
    def get_all(cls):
        return cls.objects.all()

    @method_cache(120)
    def get_file_statistics(self, timeout=30):
        queue_name = self.get_remote_queue_name('storage', "slow")
        data = storage_tasks.get_file_statistics.apply_async(
            args=[self.type, self.path], queue=queue_name).get(timeout=timeout)
        return data


class Disk(TimeStampedModel):

    """A virtual disk.
    """
    TYPES = (('qcow2-norm', 'qcow2 normal'), ('qcow2-snap', 'qcow2 snapshot'),
             ('ceph-norm', 'Ceph block normal'),
             ('ceph-snap', 'Ceph block snapshot'),
             ('iso', 'iso'), ('raw-ro', 'raw read-only'), ('raw-rw', 'raw'))
    BUS_TYPES = (('virtio', 'virtio'), ('ide', 'ide'), ('scsi', 'scsi'))

    name = CharField(blank=True, max_length=100, verbose_name=_("name"))
    filename = CharField(max_length=256, unique=True,
                         verbose_name=_("filename"),
                         validators=[validate_ascii])
    datastore = ForeignKey(DataStore, verbose_name=_("datastore"),
                           help_text=_("The datastore that holds the disk."))
    type = CharField(max_length=10, choices=TYPES)
    bus = CharField(max_length=10, choices=BUS_TYPES, null=True, blank=True,
                    default=None)
    size = FileSizeField(null=True, default=None)
    base = ForeignKey('self', blank=True, null=True,
                      related_name='derivatives')
    dev_num = CharField(default='a', max_length=1,
                        verbose_name=_("device number"))
    destroyed = DateTimeField(blank=True, default=None, null=True)

    is_ready = BooleanField(default=False)

    class Meta:
        ordering = ['name']
        verbose_name = _('disk')
        verbose_name_plural = _('disks')
        permissions = (
            ('create_empty_disk', _('Can create an empty disk.')),
            ('download_disk', _('Can download a disk.')),
            ('resize_disk', _('Can resize a disk.'))
        )

    class DiskError(HumanReadableException):
        admin_message = None

        def __init__(self, disk, params=None, level=None, **kwargs):
            kwargs.update(params or {})
            self.disc = kwargs["disk"] = disk
            super(Disk.DiskError, self).__init__(
                level, self.message, self.admin_message or self.message,
                kwargs)

    class WrongDiskTypeError(DiskError):
        message = ugettext_noop("Operation can't be invoked on disk "
                                "'%(name)s' of type '%(type)s'.")

        admin_message = ugettext_noop(
            "Operation can't be invoked on disk "
            "'%(name)s' (%(pk)s) of type '%(type)s'.")

        def __init__(self, disk, params=None, **kwargs):
            super(Disk.WrongDiskTypeError, self).__init__(
                disk, params, type=disk.type, name=disk.name, pk=disk.pk)

    class DiskInUseError(DiskError):
        message = ugettext_noop(
            "The requested operation can't be performed on "
            "disk '%(name)s' because it is in use.")

        admin_message = ugettext_noop(
            "The requested operation can't be performed on "
            "disk '%(name)s' (%(pk)s) because it is in use.")

        def __init__(self, disk, params=None, **kwargs):
            super(Disk.DiskInUseError, self).__init__(
                disk, params, name=disk.name, pk=disk.pk)

    class DiskIsNotReady(DiskError):
        message = ugettext_noop(
            "The requested operation can't be performed on "
            "disk '%(name)s' because it has never been deployed.")

        admin_message = ugettext_noop(
            "The requested operation can't be performed on "
            "disk '%(name)s' (%(pk)s) [%(filename)s] because it has never been"
            "deployed.")

        def __init__(self, disk, params=None, **kwargs):
            super(Disk.DiskIsNotReady, self).__init__(
                disk, params, name=disk.name, pk=disk.pk,
                filename=disk.filename)

    class DiskBaseIsNotReady(DiskError):
        message = ugettext_noop(
            "The requested operation can't be performed on "
            "disk '%(name)s' because its base has never been deployed.")

        admin_message = ugettext_noop(
            "The requested operation can't be performed on "
            "disk '%(name)s' (%(pk)s) [%(filename)s] because its base "
            "'%(b_name)s' (%(b_pk)s) [%(b_filename)s] has never been"
            "deployed.")

        def __init__(self, disk, params=None, **kwargs):
            base = kwargs.get('base')
            super(Disk.DiskBaseIsNotReady, self).__init__(
                disk, params, name=disk.name, pk=disk.pk,
                filename=disk.filename, b_name=base.name,
                b_pk=base.pk, b_filename=base.filename)

    @property
    def path(self):
        """The path where the files are stored.
        """
        return join(self.datastore.path, self.filename)

    @property
    def format_for_vmdriver(self):
        """Returns the proper file format for different type of images.
        """
        return {
            'qcow2-norm': 'qcow2',
            'qcow2-snap': 'qcow2',
            'ceph-norm': 'raw',
            'ceph-snap': 'raw',
            'iso': 'raw',
            'raw-ro': 'raw',
            'raw-rw': 'raw',
        }[self.type]

    @property
    def format_for_storagedriver(self):
        """Returns the proper file format for different types of images.
        """
        return {
            'qcow2-norm': 'qcow2',
            'qcow2-snap': 'qcow2',
            'ceph-norm': 'rbd',
            'ceph-snap': 'rbd',
            'iso': 'iso',
            'raw-ro': 'raw',
            'raw-rw': 'raw',
        }[self.type]

    @property
    def device_type(self):
        """Returns the proper device prefix for different types of images.
        """
        return {
            'qcow2-norm': 'vd',
            'qcow2-snap': 'vd',
            'ceph-norm': 'vd',
            'ceph-snap': 'vd',
            'iso': 'sd',
            'raw-ro': 'vd',
            'raw-rw': 'vd',
        }[self.type]

    @property
    def device_bus(self):
        """Returns the proper device prefix for different types of images.
        """
        if self.bus:
            return self.bus
        return {
            'qcow2-norm': 'virtio',
            'qcow2-snap': 'virtio',
            'ceph-norm': 'virtio',
            'ceph-snap': 'virtio',
            'iso': 'ide',
            'raw-ro': 'virtio',
            'raw-rw': 'virtio',
        }[self.type]

    @property
    def is_deletable(self):
        """True if the associated file can be deleted.
        """
        # Check if all children and the disk itself is destroyed.
        return (self.destroyed is not None) and self.children_deletable

    @property
    def children_deletable(self):
        """True if all children of the disk are deletable.
        """
        return all(i.is_deletable for i in self.derivatives.all())

    @property
    def is_in_use(self):
        """True if disk is attached to an active VM.

        'In use' means the disk is attached to a VM which is not STOPPED, as
        any other VMs leave the disk in an inconsistent state.
        """
        return any(i.state != 'STOPPED' for i in self.instance_set.all())

    def get_appliance(self):
        """Return the Instance or InstanceTemplate object where the disk
        is used
        """
        try:
            app = self.template_set.all() or self.instance_set.all()
            return app.get()
        except ObjectDoesNotExist:
            return None

    def get_exclusive(self):
        """Get an instance of the disk for exclusive usage.

        This method manipulates the database only.
        """
        type_mapping = {
            'qcow2-norm': 'qcow2-snap',
            'ceph-norm': 'ceph-snap',
            'iso': 'iso',
            'raw-ro': 'raw-rw',
        }

        if self.type not in type_mapping.keys():
            raise self.WrongDiskTypeError(self)

        new_type = type_mapping[self.type]

        return Disk.create(base=self, datastore=self.datastore,
                           name=self.name, size=self.size,
                           type=new_type, dev_num=self.dev_num)

    def get_disk_desc(self):
        """Serialize disk object to the storage driver.
        """
        if self.datastore.type == "ceph_block":
            return self.get_disk_desc_for_ceph_block_device()

        return self.get_disk_desc_for_filesystem()

    def get_vmdisk_desc(self):
        """Serialize disk object to the vmdriver.
        """
        if self.datastore.type == "ceph_block":
            return self.get_vmdisk_desc_for_ceph_block_device()

        return self.get_vmdisk_desc_for_filesystem()

    def get_disk_desc_for_filesystem(self):

        return {
            'data_store_type': self.datastore.type,
            'name': str(self.filename),
            'dir': str(self.datastore.path),
            'format': self.format_for_storagedriver,
            'size': self.size,
            'base_name': str(self.base.filename) if self.base else None,
            'type': 'snapshot' if self.base else 'normal'
        }

    def get_disk_desc_for_ceph_block_device(self):
        return self.get_disk_desc_for_filesystem()

    def get_vmdisk_desc_for_filesystem(self):

        return {
            'data_store_type': self.datastore.type,
            'source': self.path,
            'driver_type': self.format_for_vmdriver,
            'driver_cache': 'none',
            'target_device': self.device_type + self.dev_num,
            'target_bus': self.device_bus,
            'disk_device': 'cdrom' if self.type == 'iso' else 'disk'
        }

    def get_vmdisk_desc_for_ceph_block_device(self):

        desc = self.get_vmdisk_desc_for_filesystem()
        desc["ceph_user"] = self.datastore.ceph_user

        return desc

    def get_remote_queue_name(self, queue_id='storage', priority=None,
                              check_worker=True):
        """Returns the proper queue name based on the datastore.
        """
        if self.datastore:
            return self.datastore.get_remote_queue_name(queue_id, priority,
                                                        check_worker)
        else:
            return None

    def __unicode__(self):
        return u"%s (#%d)" % (self.name, self.id or 0)

    def clean(self, *args, **kwargs):
        if (self.size is None or "") and self.base:
            self.size = self.base.size

        if self.base is not None and\
           self.datastore.type != self.base.datastore.type:
            raise ValidationError(_("Forbidden inheritance of disks "
                                    "from different type of data stores."))
        super(Disk, self).clean(*args, **kwargs)

    def deploy(self, user=None, task_uuid=None, timeout=15):
        """Reify the disk model on the associated data store.

        :param self: the disk model to reify
        :type self: storage.models.Disk

        :param user: The user who's issuing the command.
        :type user: django.contrib.auth.models.User

        :param task_uuid: The task's UUID, if the command is being executed
                          asynchronously.
        :type task_uuid: str

        :return: True if a new reification of the disk has been created;
                 otherwise, False.
        :rtype: bool
        """
        if self.destroyed:
            self.destroyed = None
            self.save()

        if self.is_ready:
            return True
        if self.base and not self.base.is_ready:
            raise self.DiskBaseIsNotReady(self, base=self.base)
        queue_name = self.get_remote_queue_name('storage', priority="fast")
        disk_desc = self.get_disk_desc()
        if self.base is not None:
            storage_tasks.snapshot.apply_async(args=[disk_desc],
                                               queue=queue_name
                                               ).get(timeout=timeout)
        else:
            storage_tasks.create.apply_async(args=[disk_desc],
                                             queue=queue_name
                                             ).get(timeout=timeout)

        self.is_ready = True
        self.save()
        return True

    @staticmethod
    def get_type_for_datastore(datastore):

        if datastore.type == "ceph_block":
            return "ceph-norm"

        return "qcow2-norm"

    @classmethod
    def create(cls, user=None, **params):
        disk = cls.__create(user, params)
        disk.clean()
        disk.save()
        logger.debug(u"Disk created from: %s",
                     unicode(params.get("base", "nobase")))
        return disk

    @classmethod
    def __create(cls, user, params):
        datastore = params.pop('datastore', DataStore.get_default_datastore())
        filename = params.pop('filename', str(uuid.uuid4()))
        disk = cls(filename=filename, datastore=datastore, **params)
        return disk

    @classmethod
    def download(cls, url, datastore, task, user=None, **params):
        """Create disk object and download data from url synchronusly.

        :param url: image url to download.
        :type url: url
        :param instance: Instance or template attach the Disk to.
        :type instance: vm.models.Instance or InstanceTemplate or NoneType
        :param user: owner of the disk
        :type user: django.contrib.auth.User
        :param task_uuid: UUID of the local task
        :param abortable_task: UUID of the remote running abortable task.

        :return: The created Disk object
        :rtype: Disk
        """
        params.setdefault('name', url.split('/')[-1])
        params.setdefault('type', 'iso')
        params.setdefault('size', None)
        params.setdefault('datastore', datastore)
        disk = cls.__create(params=params, user=user)
        queue_name = disk.get_remote_queue_name('storage', priority='slow')
        remote = storage_tasks.download.apply_async(
            kwargs={'url': url, 'parent_id': task.request.id,
                    'disk': disk.get_disk_desc()},
            queue=queue_name)
        while True:
            try:
                result = remote.get(timeout=5)
                break
            except TimeoutError as e:
                if task is not None and task.is_aborted():
                    AbortableAsyncResult(remote.id).abort()
                    raise humanize_exception(ugettext_noop(
                        "Operation aborted by user."), e)
        disk.size = result['size']
        disk.type = result['type']
        disk.checksum = result.get('checksum', None)
        disk.is_ready = True
        disk.save()
        return disk

    def destroy(self, user=None, task_uuid=None):
        if self.destroyed:
            return False

        self.destroyed = timezone.now()
        self.save()
        return True

    def restore(self, user=None, task_uuid=None, timeout=15):
        """Recover destroyed disk from trash if possible.
        """
        queue_name = self.datastore.get_remote_queue_name(
            'storage', priority='slow')
        res = storage_tasks.exists.apply_async(
            args=[self.datastore.type,
                  self.datastore.path,
                  self.filename],
            queue=queue_name).get(timeout=timeout)
        if res:
            logger.info("Image: %s at Datastore: %s recovered." %
                        (self.filename, self.datastore.path))
        else:
            logger.info("Image: %s at Datastore: %s not recovered." %
                        (self.filename, self.datastore.path))

    def save_as(self, task=None, user=None, task_uuid=None, timeout=300):
        """Save VM as template.

        Based on disk type:
        qcow2-norm, qcow2-snap --> qcow2-norm
        iso                    --> iso (with base)
        ceph-norm, ceph-snap   --> ceph-norm

        VM must be in STOPPED state to perform this action.
        The timeout parameter is not used now.
        """
        mapping = {
            'qcow2-snap': ('qcow2-norm', None),
            'qcow2-norm': ('qcow2-norm', None),
            'ceph-snap': ('ceph-norm', None),
            'ceph-norm': ('ceph-norm', None),
            'iso': ("iso", self),
        }
        if self.type not in mapping.keys():
            raise self.WrongDiskTypeError(self)

        if self.is_in_use:
            raise self.DiskInUseError(self)

        if not self.is_ready:
            raise self.DiskIsNotReady(self)

        # from this point on, the caller has to guarantee that the disk is not
        # going to be used until the operation is complete

        new_type, new_base = mapping[self.type]

        disk = Disk.create(datastore=self.datastore,
                           base=new_base,
                           name=self.name, size=self.size,
                           type=new_type, dev_num=self.dev_num)

        queue_name = self.get_remote_queue_name("storage", priority="slow")
        remote = storage_tasks.merge.apply_async(kwargs={
            "old_json": self.get_disk_desc(),
            "new_json": disk.get_disk_desc(),
            "parent_id": task.request.id},
            queue=queue_name
        )  # Timeout
        while True:
            try:
                remote.get(timeout=5)
                break
            except TimeoutError as e:
                if task is not None and task.is_aborted():
                    AbortableAsyncResult(remote.id).abort()
                    disk.destroy()
                    raise humanize_exception(ugettext_noop(
                        "Operation aborted by user."), e)
            except:
                disk.destroy()
                raise
        disk.is_ready = True
        disk.save()
        return disk

    def get_absolute_url(self):
        return reverse('dashboard.views.disk-detail', kwargs={'pk': self.pk})

    @property
    def is_resizable(self):
        return self.type in ('qcow2-norm', 'raw-rw', 'qcow2-snap', )
