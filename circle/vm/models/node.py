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

from common.models import method_cache, WorkerNotFound
from firewall.models import Host
from ..tasks import vm_tasks
from .common import Trait

from .activity import node_activity, NodeActivity

from monitor.calvin.calvin import Query
from monitor.calvin.calvin import GraphiteHandler
from django.utils import timezone

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

    @method_cache(10, 5)
    def get_online(self):
        """Check if the node is online.

        Runs a remote ping task if the worker is running.
        """
        try:
            return self.remote_query(vm_tasks.ping, timeout=1, default=False)
        except WorkerNotFound:
            return False

    online = property(get_online)

    @method_cache(300)
    def get_num_cores(self):
        """Number of CPU threads available to the virtual machines.
        """

        return self.remote_query(vm_tasks.get_core_num, default=0)

    num_cores = property(get_num_cores)

    @property
    def state(self):
        """The state combined of online and enabled attributes.
        """
        if self.enabled and self.online:
            return 'ONLINE'
        elif self.enabled and not self.online:
            return 'MISSING'
        elif not self.enabled and self.online:
            return 'DISABLED'
        else:
            return 'OFFLINE'

    def disable(self, user=None):
        ''' Disable the node.'''
        if self.enabled is True:
            with node_activity(code_suffix='disable', node=self, user=user):
                self.enabled = False
                self.save()

    def enable(self, user=None):
        ''' Enable the node. '''
        if self.enabled is not True:
            with node_activity(code_suffix='enable', node=self, user=user):
                self.enabled = True
                self.save()
            self.get_num_cores(invalidate_cache=True)
            self.get_ram_size(invalidate_cache=True)

    @method_cache(300)
    def get_ram_size(self):
        """Bytes of total memory in the node.
        """
        return self.remote_query(vm_tasks.get_ram_size, default=0)

    ram_size = property(get_ram_size)

    @property
    def ram_size_with_overcommit(self):
        """Bytes of total memory including overcommit margin.
        """
        return self.ram_size * self.overcommit

    @method_cache(30)
    def get_remote_queue_name(self, queue_id):
        """Return the name of the remote celery queue for this node.

        throws Exception if there is no worker on the queue.
        Until the cache provide reult there can be dead queues.
        """

        if vm_tasks.check_queue(self.host.hostname, queue_id):
            self.node_online()
            return self.host.hostname + "." + queue_id
        else:
            if self.enabled is True:
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
                act = NodeActivity.create(code_suffix='monitor_succes_online',
                                          node=self, user=None)
                act.started = timezone.now()
                act.finished = timezone.now()
                act.succeeded = True
                act.save()
                logger.info("Node %s is ONLINE." % self.name)
                self.get_num_cores(invalidate_cache=True)
                self.get_ram_size(invalidate_cache=True)

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

    def get_monitor_info(self):
        collected = {}
        try:
            handler = GraphiteHandler()
        except:
            response = self.remote_query(vm_tasks.get_node_metrics, 30)
            collected['cpu.usage'] = response['cpu.usage']
            collected['memory.usage'] = response['memory.usage']
            return collected
        query = Query()
        query.set_target(self.host.hostname + ".circle")
        query.set_format("json")
        query.set_relative_start(5, "minutes")
        metrics = ["cpu.usage", "memory.usage"]
        collected = {}
        for metric in metrics:
            query.set_metric(metric)
            query.generate()
            handler.put(query)
            handler.send()
        for metric in metrics:
            response = handler.pop()
            length = len(response[0]["datapoints"])
            cache = response[0]["datapoints"][length - 1][0]
            if cache is None:
                cache = 0
            collected[metric] = cache
        return collected

    @property
    def cpu_usage(self):
        return float(self.get_monitor_info()["cpu.usage"]) / 100

    @property
    def ram_usage(self):
        return float(self.get_monitor_info()["memory.usage"]) / 100

    @property
    def byte_ram_usage(self):
        return self.ram_usage * self.ram_size

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
        return len([1 for i in cls.objects.filter(enabled=enabled).all()
                    if i.online == online])

    @permalink
    def get_absolute_url(self):
        return ('dashboard.views.node-detail', None, {'pk': self.id})
