from __future__ import absolute_import, unicode_literals
from logging import getLogger
from warnings import warn

from django.db.models import (
    CharField, IntegerField, ForeignKey, BooleanField, ManyToManyField,
    FloatField, permalink,
)
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from celery.exceptions import TimeoutError
from model_utils.models import TimeStampedModel
from taggit.managers import TaggableManager

from common.models import method_cache, WorkerNotFound, HumanSortField
from common.operations import OperatedMixin
from firewall.models import Host
from monitor.calvin.calvin import Query
from monitor.calvin.calvin import GraphiteHandler
from ..tasks import vm_tasks
from .activity import node_activity, NodeActivity
from .common import Trait


logger = getLogger(__name__)


def node_available(function):
    """Decorate methods to ignore disabled Nodes.
    """
    def decorate(self, *args, **kwargs):
        if self.enabled and self.online:
            return function(self, *args, **kwargs)
        else:
            return None
    return decorate


class Node(OperatedMixin, TimeStampedModel):

    """A VM host machine, a hypervisor.
    """
    name = CharField(max_length=50, unique=True,
                     verbose_name=_('name'),
                     help_text=_('Human readable name of node.'))
    normalized_name = HumanSortField(monitor='name', max_length=100)
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
        ordering = ('-enabled', 'normalized_name')

    def __unicode__(self):
        return self.name

    @method_cache(10)
    def get_online(self):
        """Check if the node is online.

        Check if node is online by queue is available.
        """
        try:
            self.get_remote_queue_name("vm")
        except:
            return False
        else:
            return True

    online = property(get_online)

    @node_available
    @method_cache(300)
    def get_info(self):
        return self.remote_query(vm_tasks.get_info,
                                 default={'core_num': '',
                                          'ram_size': '0',
                                          'architecture': ''})

    info = property(get_info)

    @property
    def ram_size(self):
        warn('Use Node.info["ram_size"]', DeprecationWarning)
        return self.info['ram_size']

    @property
    def num_cores(self):
        warn('Use Node.info["core_num"]', DeprecationWarning)
        return self.info['core_num']

    STATES = {False: {False: ('OFFLINE', _('offline')),
                      True: ('DISABLED', _('disabled'))},
              True: {False: ('MISSING', _('missing')),
                     True: ('ONLINE', _('online'))}}

    def get_state(self):
        """The state combined of online and enabled attributes.
        """
        return self.STATES[self.enabled][self.online][0]

    state = property(get_state)

    def get_status_display(self):
        return self.STATES[self.enabled][self.online][1]

    def disable(self, user=None, base_activity=None):
        ''' Disable the node.'''
        if self.enabled:
            if base_activity:
                act_ctx = base_activity.sub_activity('disable')
            else:
                act_ctx = node_activity('disable', node=self, user=user)
            with act_ctx:
                self.enabled = False
                self.save()

    def enable(self, user=None):
        ''' Enable the node. '''
        if self.enabled is not True:
            with node_activity(code_suffix='enable', node=self, user=user):
                self.enabled = True
                self.save()
            self.get_info(invalidate_cache=True)

    @property
    @node_available
    def ram_size_with_overcommit(self):
        """Bytes of total memory including overcommit margin.
        """
        return self.ram_size * self.overcommit

    @method_cache(30)
    def get_remote_queue_name(self, queue_id):
        """Returns the name of the remote celery queue for this node.

        Throws Exception if there is no worker on the queue.
        The result may include dead queues because of caching.
        """

        if vm_tasks.check_queue(self.host.hostname, queue_id):
            self.node_online()
            return self.host.hostname + "." + queue_id
        else:
            if self.enabled:
                self.node_offline()
            raise WorkerNotFound()

    def node_online(self):
        """Create activity and log entry when node reappears.
        """

        try:
            act = self.activity_log.order_by('-pk')[0]
        except IndexError:
            pass  # no monitoring activity at all
        else:
            logger.debug("The last activity was %s" % act)
            if act.activity_code.endswith("offline"):
                act = NodeActivity.create(code_suffix='monitor_success_online',
                                          node=self, user=None)
                act.started = timezone.now()
                act.finished = timezone.now()
                act.succeeded = True
                act.save()
                logger.info("Node %s is ONLINE." % self.name)
                self.get_info(invalidate_cache=True)

    def node_offline(self):
        """Called when a node disappears.

        If the node is not already offline, record an activity and a log entry.
        """

        try:
            act = self.activity_log.order_by('-pk')[0]
        except IndexError:
            pass  # no activity at all
        else:
            logger.debug("The last activity was %s" % act)
            if act.activity_code.endswith("offline"):
                return
        act = NodeActivity.create(code_suffix='monitor_failed_offline',
                                  node=self, user=None)
        act.started = timezone.now()
        act.finished = timezone.now()
        act.succeeded = False
        act.save()
        logger.critical("Node %s is OFFLINE%s.", self.name,
                        ", but enabled" if self.enabled else "")
        # TODO: check if we should reschedule any VMs?

    def remote_query(self, task, timeout=30, raise_=False, default=None):
        """Query the given task, and get the result.

        If the result is not ready or worker not reachable
        in timeout secs, return default value or raise a
        TimeoutError or WorkerNotFound exception.
        """
        try:
            r = task.apply_async(
                queue=self.get_remote_queue_name('vm'), expires=timeout + 60)
            return r.get(timeout=timeout)
        except (TimeoutError, WorkerNotFound):
            if raise_:
                raise
            else:
                return default

    @node_available
    def get_monitor_info(self):
        try:
            handler = GraphiteHandler()
        except RuntimeError:
            return self.remote_query(vm_tasks.get_node_metrics, 30)

        query = Query()
        query.set_target(self.host.hostname + ".circle")
        query.set_format("json")
        query.set_relative_start(5, "minutes")

        metrics = ["cpu.usage", "memory.usage"]
        for metric in metrics:
            query.set_metric(metric)
            query.generate()
            handler.put(query)
            handler.send()

        collected = {}
        for metric in metrics:
            response = handler.pop()
            try:
                cache = response[0]["datapoints"][-1][0]
            except (IndexError, KeyError):
                cache = 0
            if cache is None:
                cache = 0
            collected[metric] = cache
        return collected

    @property
    @node_available
    def cpu_usage(self):
        return float(self.get_monitor_info()["cpu.usage"]) / 100

    @property
    @node_available
    def ram_usage(self):
        return float(self.get_monitor_info()["memory.usage"]) / 100

    @property
    @node_available
    def byte_ram_usage(self):
        return self.ram_usage * self.ram_size

    @node_available
    def update_vm_states(self):
        """Update state of Instances running on this Node.

        Query state of all libvirt domains, and notify Instances by their
        vm_state_changed hook.
        """
        domains = {}
        domain_list = self.remote_query(vm_tasks.list_domains_info, timeout=5)
        if domain_list is None:
            logger.info("Monitoring failed at: %s", self.name)
            return
        for i in domain_list:
            # [{'name': 'cloud-1234', 'state': 'RUNNING', ...}, ...]
            try:
                id = int(i['name'].split('-')[1])
            except:
                pass  # name format doesn't match
            else:
                domains[id] = i['state']

        instances = [{'id': i.id, 'state': i.state}
                     for i in self.instance_set.order_by('id').all()]
        for i in instances:
            try:
                d = domains[i['id']]
            except KeyError:
                logger.info('Node %s update: instance %s missing from '
                            'libvirt', self, i['id'])
                # Set state to STOPPED when instance is missing
                self.instance_set.get(id=i['id']).vm_state_changed('STOPPED')
            else:
                if d != i['state']:
                    logger.info('Node %s update: instance %s state changed '
                                '(libvirt: %s, db: %s)',
                                self, i['id'], d, i['state'])
                    self.instance_set.get(id=i['id']).vm_state_changed(d)

                del domains[i['id']]
        for i in domains.keys():
            logger.info('Node %s update: domain %s in libvirt but not in db.',
                        self, i)

    @classmethod
    def get_state_count(cls, online, enabled):
        return len([1 for i in
                    cls.objects.filter(enabled=enabled).select_related('host')
                    if i.online == online])

    @permalink
    def get_absolute_url(self):
        return ('dashboard.views.node-detail', None, {'pk': self.id})
