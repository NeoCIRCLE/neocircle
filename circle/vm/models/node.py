from __future__ import unicode_literals
from datetime import timedelta
from logging import getLogger

from django.db.models import (
    Model, CharField, IntegerField, ForeignKey, BooleanField, ManyToManyField,
    FloatField,
)
from django.utils.translation import ugettext_lazy as _

from celery.exceptions import TimeoutError
from model_utils.models import TimeStampedModel
from taggit.managers import TaggableManager

from common.models import method_cache
from firewall.models import Host
from ..tasks import vm_tasks

logger = getLogger(__name__)


class Trait(Model):
    name = CharField(max_length=50, verbose_name=_('name'))

    class Meta:
        app_label = 'vm'
        db_table = 'vm_trait'

    def __unicode__(self):
        return self.name


class Node(TimeStampedModel):

    """A VM host machine, a hypervisor.
    """
    name = CharField(max_length=50, unique=True,
                     verbose_name=_('name'),
                     help_text=_('Human readable name of node.'))
    priority = IntegerField(verbose_name=_('priority'),
                            help_text=_('Node usage priority.'))
    host = ForeignKey(Host, verbose_name=_('host'),
                      help_text=_('Host in firewall.'))
    enabled = BooleanField(verbose_name=_('enabled'), default=False,
                           help_text=_('Indicates whether the node can '
                                       'be used for hosting.'))
    traits = ManyToManyField(Trait, blank=True,
                             help_text=_("Declared traits."),
                             verbose_name=_('traits'))
    tags = TaggableManager(blank=True, verbose_name=_("tags"))
    overcommit = FloatField(default=1.0, verbose_name=_("overcommit ratio"),
                            help_text=_("The ratio of total memory with "
                                        "to without overcommit."))

    class Meta:
        app_label = 'vm'
        db_table = 'vm_node'
        permissions = ()

    @property
    @method_cache(10, 5)
    def online(self):

        return self.remote_query(vm_tasks.get_core_num, timeout=1,
                                 default=False)

    @property
    @method_cache(300)
    def num_cores(self):
        """Number of CPU threads available to the virtual machines."""

        return self.remote_query(vm_tasks.get_core_num)

    @property
    @method_cache(300)
    def ram_size(self):
        """Bytes of total memory in the node."""

        return self.remote_query(vm_tasks.get_ram_size)

    @property
    def ram_size_with_overcommit(self):
        """Bytes of total memory including overcommit margin.
        """
        return self.ram_size * self.overcommit

    def get_remote_queue_name(self, queue_id):
        return self.host.hostname + "." + queue_id

    def remote_query(self, task, timeout=30, raise_=False, default=None):
        """Query the given task, and get the result.

        If the result is not ready in timeout secs, return default value or
        raise a TimeoutError."""
        r = task.apply_async(
            queue=self.get_remote_queue_name('vm'), expires=timeout + 60)
        try:
            return r.get(timeout=timeout)
        except TimeoutError:
            if raise_:
                raise
            else:
                return default

    def update_vm_states(self):
        domains = {}
        for i in self.remote_query(vm_tasks.list_domains_info, timeout=5):
            # [{'name': 'cloud-1234', 'state': 'RUNNING', ...}, ...]
            try:
                id = int(i['name'].split('-')[1])
            except:
                pass  # name format doesn't match
            else:
                domains[id] = i['state']

        instances = self.instance_set.order_by('id').values('id', 'state')
        for i in instances:
            try:
                d = domains[i['id']]
            except KeyError:
                logger.info('Node %s update: instance %s missing from '
                            'libvirt', self, i['id'])
            else:
                if d != i['state']:
                    logger.info('Node %s update: instance %s state changed '
                                '(libvirt: %s, db: %s)',
                                self, i['id'], d, i['state'])
                    self.instance_set.get(id=i['id']).state_changed(d)

                del domains[i['id']]
        for i in domains.keys():
            logger.info('Node %s update: domain %s in libvirt but not in db.',
                        self, i)

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

    def __unicode__(self):
        return self.name
