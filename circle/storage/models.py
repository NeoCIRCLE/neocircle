# coding=utf-8

from contextlib import contextmanager
import logging
import uuid

from django.db.models import (Model, BooleanField, CharField, DateTimeField,
                              ForeignKey)
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from sizefield.models import FileSizeField

from acl.models import AclBase
from .tasks import local_tasks, remote_tasks
from common.models import ActivityModel, activitycontextimpl

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

    def get_remote_queue_name(self, queue_id):
        return self.hostname + '.' + queue_id


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
        return self.datastore.path + '/' + self.filename

    @property
    def format(self):
        return {
            'qcow2-norm': 'qcow2',
            'qcow2-snap': 'qcow2',
            'iso': 'raw',
            'raw-ro': 'raw',
            'raw-rw': 'raw',
        }[self.type]

    @property
    def device_type(self):
        return {
            'qcow2-norm': 'vd',
            'qcow2-snap': 'vd',
            'iso': 'hd',
            'raw-ro': 'vd',
            'raw-rw': 'vd',
        }[self.type]

    def is_in_use(self):
        return self.instance_set.exclude(state='SHUTOFF').exists()

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
            'target_device': self.device_type + self.dev_num,
            'disk_device': 'cdrom' if self.type == 'iso' else 'disk'
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

    def get_remote_queue_name(self, queue_id):
        if self.datastore:
            return self.datastore.get_remote_queue_name(queue_id)
        else:
            return None

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
                                                      queue=queue_name).get()
            else:
                with act.sub_activity('creating_disk'):
                    remote_tasks.create.apply_async(args=[disk_desc],
                                                    queue=queue_name).get()

            self.ready = True
            self.save()

            return True

    def deploy_async(self, user=None):
        """Execute deploy asynchronously.
        """
        return local_tasks.deploy.apply_async(args=[self, user],
                                              queue="localhost.man")

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
        """Restore destroyed disk.
        """
        # TODO
        pass

    def restore_async(self, user=None):
        local_tasks.restore.apply_async(args=[self, user],
                                        queue='localhost.man')

    def save_as(self, user=None, task_uuid=None):
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
                           task_uuid=task_uuid, user=user):

            filename = str(uuid.uuid4())
            new_type, new_base = mapping[self.type]

            disk = Disk.objects.create(base=new_base, datastore=self.datastore,
                                       filename=filename, name=self.name,
                                       size=self.size, type=new_type)

            queue_name = self.get_remote_queue_name('storage')
            remote_tasks.merge.apply_async(args=[self.get_disk_desc(),
                                                 disk.get_disk_desc()],
                                           queue=queue_name).get()

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
def disk_activity(code_suffix, disk, task_uuid=None, user=None):
    act = DiskActivity.create(code_suffix, disk, task_uuid, user)
    return activitycontextimpl(act)
