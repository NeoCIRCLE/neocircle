# coding=utf-8

from contextlib import contextmanager
import logging
from os.path import join
import uuid

from django.db.models import (Model, BooleanField, CharField, DateTimeField,
                              ForeignKey)
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from sizefield.models import FileSizeField
from datetime import timedelta

from acl.models import AclBase
from .tasks import local_tasks, remote_tasks
from celery.exceptions import TimeoutError
from common.models import ActivityModel, activitycontextimpl, WorkerNotFound

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

    def get_remote_queue_name(self, queue_id, check_worker=True):
        logger.debug("Checking for storage queue %s.%s",
                     self.hostname, queue_id)
        if not check_worker or local_tasks.check_queue(self.hostname,
                                                       queue_id):
            return self.hostname + '.' + queue_id
        else:
            raise WorkerNotFound()

    def get_deletable_disks(self):
        return [disk.filename for disk in
                self.disk_set.filter(
                    destroyed__isnull=False) if disk.is_deletable()]


class Disk(AclBase, TimeStampedModel):

    """A virtual disk.
    """
    ACL_LEVELS = (
        ('user', _('user')),          # see all details
        ('operator', _('operator')),
        ('owner', _('owner')),        # superuser, can delete, delegate perms
    )
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
    ready = BooleanField(default=False,
                         help_text=_("The associated resource is ready."))
    dev_num = CharField(default='a', max_length=1,
                        verbose_name=_("device number"))
    destroyed = DateTimeField(blank=True, default=None, null=True)

    class Meta:
        ordering = ['name']
        verbose_name = _('disk')
        verbose_name_plural = _('disks')

    class WrongDiskTypeError(Exception):

        def __init__(self, type, message=None):
            if message is None:
                message = ("Operation can't be invoked on a disk of type '%s'."
                           % type)

            Exception.__init__(self, message)

            self.type = type

    class DiskInUseError(Exception):

        def __init__(self, disk, message=None):
            if message is None:
                message = ("The requested operation can't be performed on "
                           "disk '%s (%s)' because it is in use." %
                           (disk.name, disk.filename))

            Exception.__init__(self, message)

            self.disk = disk

    @property
    def path(self):
        """Get the path where the files are stored."""
        return join(self.datastore.path, self.filename)

    @property
    def format(self):
        """Returns the proper file format for different type of images."""
        return {
            'qcow2-norm': 'qcow2',
            'qcow2-snap': 'qcow2',
            'iso': 'raw',
            'raw-ro': 'raw',
            'raw-rw': 'raw',
        }[self.type]

    @property
    def device_type(self):
        """Returns the proper device prefix for different file format."""
        return {
            'qcow2-norm': 'vd',
            'qcow2-snap': 'vd',
            'iso': 'hd',
            'raw-ro': 'vd',
            'raw-rw': 'vd',
        }[self.type]

    def is_deletable(self):
        """Returns whether the file can be deleted.

        Checks if all children and the disk itself is destroyed.
        """

        yesterday = timezone.now() - timedelta(days=1)
        return (self.destroyed is not None
                and self.destroyed < yesterday) and not self.has_active_child()

    def has_active_child(self):
        """Returns if disk has children that are not destroyed.
        """

        return any((not i.is_deletable() for i in self.derivatives.all()))

    def is_in_use(self):
        """Returns if disk is attached to an active VM.

        'In use' means the disk is attached to a VM which is not STOPPED, as
        any other VMs leave the disk in an inconsistent state.
        """
        return any([i.state != 'STOPPED' for i in self.instance_set.all()])

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

        filename = self.filename if self.type == 'iso' else None
        new_type = type_mapping[self.type]

        return Disk.objects.create(base=self, datastore=self.datastore,
                                   filename=filename, name=self.name,
                                   size=self.size, type=new_type)

    def get_vmdisk_desc(self):
        """Serialize disk object to the vmdriver."""
        return {
            'source': self.path,
            'driver_type': self.format,
            'driver_cache': 'none',
            'target_device': self.device_type + self.dev_num,
            'disk_device': 'cdrom' if self.type == 'iso' else 'disk'
        }

    def get_disk_desc(self):
        """Serialize disk object to the storage driver."""
        return {
            'name': self.filename,
            'dir': self.datastore.path,
            'format': self.format,
            'size': self.size,
            'base_name': self.base.filename if self.base else None,
            'type': 'snapshot' if self.type == 'qcow2-snap' else 'normal'
        }

    def get_remote_queue_name(self, queue_id='storage', check_worker=True):
        """Returns the proper queue name based on the datastore."""
        if self.datastore:
            return self.datastore.get_remote_queue_name(queue_id, check_worker)
        else:
            return None

    def __unicode__(self):
        return u"%s (#%d)" % (self.name, self.id or 0)

    def clean(self, *args, **kwargs):
        if self.size == "" and self.base:
            self.size = self.base.size
        super(Disk, self).clean(*args, **kwargs)

    def save(self, *args, **kwargs):
        if self.filename is None:
            self.generate_filename()
        return super(Disk, self).save(*args, **kwargs)

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

        if self.ready:
            return False

        with disk_activity(code_suffix='deploy', disk=self,
                           task_uuid=task_uuid, user=user) as act:

            # Delegate create / snapshot jobs
            queue_name = self.get_remote_queue_name('storage')
            disk_desc = self.get_disk_desc()
            if self.type == 'qcow2-snap':
                with act.sub_activity('creating_snapshot'):
                    remote_tasks.snapshot.apply_async(args=[disk_desc],
                                                      queue=queue_name
                                                      ).get(timeout=timeout)
            else:
                with act.sub_activity('creating_disk'):
                    remote_tasks.create.apply_async(args=[disk_desc],
                                                    queue=queue_name
                                                    ).get(timeout=timeout)

            self.ready = True
            self.save()

            return True

    def deploy_async(self, user=None):
        """Execute deploy asynchronously.
        """
        return local_tasks.deploy.apply_async(args=[self, user],
                                              queue="localhost.man")

    def generate_filename(self):
        """Generate a unique filename and set it on the object.
        """
        self.filename = str(uuid.uuid4())

    @classmethod
    def create_empty(cls, instance=None, user=None, **kwargs):
        """Create empty Disk object.

        :param instance: Instance or template attach the Disk to.
        :type instance: vm.models.Instance or InstanceTemplate or NoneType
        :param user: Creator of the disk.
        :type user: django.contrib.auth.User

        :return: Disk object without a real image, to be .deploy()ed later.
        """

        disk = cls.objects.create(**kwargs)
        with disk_activity(code_suffix="create", user=user, disk=disk):
            if instance:
                instance.disks.add(disk)
            return disk

    @classmethod
    def create_from_url_async(cls, url, instance=None, user=None, **kwargs):
        """Create disk object and download data from url asynchrnously.

        :param url: URL of image to download.
        :type url: string
        :param instance: Instance or template attach the Disk to.
        :type instance: vm.models.Instance or InstanceTemplate or NoneType
        :param user: owner of the disk
        :type user: django.contrib.auth.User

        :return: Task
        :rtype: AsyncResult
        """
        kwargs.update({'cls': cls, 'url': url,
                       'instance': instance, 'user': user})
        return local_tasks.create_from_url.apply_async(
            kwargs=kwargs, queue='localhost.man')

    @classmethod
    def create_from_url(cls, url, instance=None, user=None,
                        task_uuid=None, abortable_task=None, **kwargs):
        """Create disk object and download data from url synchronusly.

        :param url: image url to download.
        :type url: url
        :param instance: Instance or template attach the Disk to.
        :type instance: vm.models.Instance or InstanceTemplate or NoneType
        :param user: owner of the disk
        :type user: django.contrib.auth.User
        :param task_uuid: TODO
        :param abortable_task: TODO

        :return: The created Disk object
        :rtype: Disk
        """
        kwargs.setdefault('name', url.split('/')[-1])
        disk = cls(**kwargs)
        disk.generate_filename()
        disk.type = "iso"
        disk.size = 1
        # TODO get proper datastore
        disk.datastore = DataStore.objects.get()
        disk.save()
        if instance:
            instance.disks.add(disk)
        queue_name = disk.get_remote_queue_name('storage')

        def __on_abort(activity, error):
            activity.disk.destroyed = timezone.now()
            activity.disk.save()

        if abortable_task:
            from celery.contrib.abortable import AbortableAsyncResult

            class AbortException(Exception):
                pass

        with disk_activity(code_suffix='download', disk=disk,
                           task_uuid=task_uuid, user=user,
                           on_abort=__on_abort):
            result = remote_tasks.download.apply_async(
                kwargs={'url': url, 'parent_id': task_uuid,
                        'disk': disk.get_disk_desc()},
                queue=queue_name)
            while True:
                try:
                    size = result.get(timeout=5)
                    break
                except TimeoutError:
                    if abortable_task and abortable_task.is_aborted():
                        AbortableAsyncResult(result.id).abort()
                        raise AbortException("Download aborted by user.")
            disk.size = size
            disk.ready = True
            disk.save()
        return disk

    def destroy(self, user=None, task_uuid=None):
        if self.destroyed:
            return False

        with disk_activity(code_suffix='destroy', disk=self,
                           task_uuid=task_uuid, user=user):
            self.destroyed = timezone.now()
            self.save()

            return True

    def destroy_async(self, user=None):
        """Execute destroy asynchronously.
        """
        return local_tasks.destroy.apply_async(args=[self, user],
                                               queue='localhost.man')

    def restore(self, user=None, task_uuid=None):
        """Recover destroyed disk from trash if possible.
        """
        # TODO
        pass

    def restore_async(self, user=None):
        local_tasks.restore.apply_async(args=[self, user],
                                        queue='localhost.man')

    def save_as(self, user=None, task_uuid=None, timeout=120):
        mapping = {
            'qcow2-snap': ('qcow2-norm', self.base),
        }
        if self.type not in mapping.keys():
            raise self.WrongDiskTypeError(self.type)

        if self.is_in_use():
            raise self.DiskInUseError(self)

        # from this point on, the caller has to guarantee that the disk is not
        # going to be used until the operation is complete

        with disk_activity(code_suffix='save_as', disk=self,
                           task_uuid=task_uuid, user=user, timeout=300):

            new_type, new_base = mapping[self.type]

            disk = Disk.objects.create(base=new_base, datastore=self.datastore,
                                       name=self.name, size=self.size,
                                       type=new_type)

            queue_name = self.get_remote_queue_name('storage')
            remote_tasks.merge.apply_async(args=[self.get_disk_desc(),
                                                 disk.get_disk_desc()],
                                           queue=queue_name
                                           ).get(timeout=timeout)

            disk.ready = True
            disk.save()

            return disk


class DiskActivity(ActivityModel):
    disk = ForeignKey(Disk, related_name='activity_log',
                      help_text=_('Disk this activity works on.'),
                      verbose_name=_('disk'))

    @classmethod
    def create(cls, code_suffix, disk, task_uuid=None, user=None):
        act = cls(activity_code='storage.Disk.' + code_suffix,
                  disk=disk, parent=None, started=timezone.now(),
                  task_uuid=task_uuid, user=user)
        act.save()
        return act

    def create_sub(self, code_suffix, task_uuid=None):
        act = DiskActivity(
            activity_code=self.activity_code + '.' + code_suffix,
            disk=self.disk, parent=self, started=timezone.now(),
            task_uuid=task_uuid, user=self.user)
        act.save()
        return act

    @contextmanager
    def sub_activity(self, code_suffix, task_uuid=None):
        act = self.create_sub(code_suffix, task_uuid)
        return activitycontextimpl(act)


@contextmanager
def disk_activity(code_suffix, disk, task_uuid=None, user=None,
                  on_abort=None, on_commit=None):
    act = DiskActivity.create(code_suffix, disk, task_uuid, user)
    return activitycontextimpl(act, on_abort=on_abort, on_commit=on_commit)
