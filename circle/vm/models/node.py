from __future__ import absolute_import, unicode_literals
from logging import getLogger

from django.db.models import (
    CharField, IntegerField, ForeignKey, BooleanField, ManyToManyField,
    FloatField, permalink,
)
from django.utils.translation import ugettext_lazy as _

from celery.exceptions import TimeoutError
from model_utils.models import TimeStampedModel
from taggit.managers import TaggableManager

from common.models import method_cache
from firewall.models import Host
from ..tasks import vm_tasks
from .common import Trait

logger = getLogger(__name__)


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

    def __unicode__(self):
        return self.name

    @property
    @method_cache(10, 5)
    def online(self):

        return self.remote_query(vm_tasks.ping, timeout=1, default=False)

    @property
    @method_cache(300)
    def num_cores(self):
        """Number of CPU threads available to the virtual machines.
        """
        return self.remote_query(vm_tasks.get_core_num)

    @property
    def state(self):
        """Node state.
        """

        if self.enabled and self.online:
            return 'online'
        elif self.enabled and not self.online:
            return 'missing'
        elif not self.enabled and self.online:
            return 'disabled'
        else:
            return 'offline'

    @property
    @method_cache(300)
    def ram_size(self):
        """Bytes of total memory in the node.
        """

        return self.remote_query(vm_tasks.get_ram_size)

    @property
    def ram_size_with_overcommit(self):
        """Bytes of total memory including overcommit margin.
        """
        return self.ram_size * self.overcommit

    def get_remote_queue_name(self, queue_id):
        return self.host.hostname + "." + queue_id

    def remote_query(self, task, timeout=1, raise_=False, default=None):
        """Query the given task, and get the result.

        If the result is not ready in timeout secs, return default value or
        raise a TimeoutError."""
        if task != vm_tasks.ping and not self.online:
            return default
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

    @classmethod
    def get_state_count(cls, online, enabled):
        return len([1 for i in cls.objects.filter(enabled=enabled).all()
                    if i.online == online])

    @permalink
    def get_absolute_url(self):
        return ('dashboard.views.node-detail', None, {'pk': self.id})
