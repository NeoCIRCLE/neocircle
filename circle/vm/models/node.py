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

from __future__ import absolute_import, unicode_literals
from functools import update_wrapper
from glob import glob
from logging import getLogger
import os.path
from warnings import warn
import requests
from salt.client import LocalClient
from salt.exceptions import SaltClientError
import salt.utils
from time import time, sleep

from django.conf import settings
from django.db.models import (
    CharField, IntegerField, ForeignKey, BooleanField, ManyToManyField,
    FloatField, DateTimeField, permalink, Sum
)
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from celery.exceptions import TimeoutError
from model_utils.models import TimeStampedModel
from taggit.managers import TaggableManager

from common.models import method_cache, WorkerNotFound, HumanSortField
from common.operations import OperatedMixin
from firewall.models import Host
from ..tasks import vm_tasks
from .activity import NodeActivity
from .common import Trait


logger = getLogger(__name__)


class MyLocalClient(LocalClient):
    def get_returns(self, jid, minions, timeout=None):
        '''
        Get the returns for the command line interface via the event system
        '''
        minions = set(minions)
        if timeout is None:
            timeout = self.opts['timeout']
        jid_dir = salt.utils.jid_dir(jid,
                                     self.opts['cachedir'],
                                     self.opts['hash_type'])
        start = time()
        timeout_at = start + timeout

        found = set()
        ret = {}
        wtag = os.path.join(jid_dir, 'wtag*')
        # Check to see if the jid is real, if not return the empty dict
        if not os.path.isdir(jid_dir):
            logger.warning("jid_dir (%s) does not exist", jid_dir)
            return ret
        # Wait for the hosts to check in
        while True:
            time_left = timeout_at - time()
            raw = self.event.get_event(time_left, jid)
            if raw is not None and 'return' in raw:
                found.add(raw['id'])
                ret[raw['id']] = raw['return']
                if len(found.intersection(minions)) >= len(minions):
                    # All minions have returned, break out of the loop
                    logger.debug("jid %s found all minions", jid)
                    break
                continue
            # Then event system timeout was reached and nothing was returned
            if len(found.intersection(minions)) >= len(minions):
                # All minions have returned, break out of the loop
                logger.debug("jid %s found all minions", jid)
                break
            if glob(wtag) and time() <= timeout_at + 1:
                # The timeout +1 has not been reached and there is still a
                # write tag for the syndic
                continue
            if time() > timeout_at:
                logger.info('jid %s minions %s did not return in time',
                            jid, (minions - found))
                break
            sleep(0.01)
        return ret


def node_available(function):
    """Decorate methods to ignore disabled Nodes.
    """
    def decorate(self, *args, **kwargs):
        if self.enabled and self.online:
            return function(self, *args, **kwargs)
        else:
            return None
    update_wrapper(decorate, function)
    decorate._original = function
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
    schedule_enabled = BooleanField(
        verbose_name=_('schedule enabled'),
        default=False,
        help_text=_(
            'Indicates whether a vm can be '
            'automatically scheduled to this '
            'node.'
        )
    )
    traits = ManyToManyField(Trait, blank=True,
                             help_text=_("Declared traits."),
                             verbose_name=_('traits'))
    tags = TaggableManager(blank=True, verbose_name=_("tags"))
    overcommit = FloatField(default=1.0, verbose_name=_("overcommit ratio"),
                            help_text=_("The ratio of total memory with "
                                        "to without overcommit."))
    ram_weight = FloatField(
        default=1.0,
        help_text=_("Indicates the relative RAM quantity of this node."),
        verbose_name=_("RAM Weight")
    )
    cpu_weight = FloatField(
        default=1.0,
        help_text=_("Indicates the relative CPU power of this node."),
        verbose_name=_("CPU Weight")
    )
    time_stamp = DateTimeField(
        auto_now_add=True,
        help_text=_("A timestamp for the node, used by the scheduler."),
        verbose_name=_("Last Scheduled Time Stamp")
    )

    class Meta:
        app_label = 'vm'
        db_table = 'vm_node'
        permissions = (
            ('view_statistics', _('Can view Node box and statistics.')),
        )
        ordering = ('-enabled', 'normalized_name')

    def __unicode__(self):
        return self.name

    @method_cache(10)
    def get_online(self):
        """Check if the node is online.

        Check if node is online by queue is available.
        """
        try:
            self.get_remote_queue_name("vm", "fast")
            self.get_remote_queue_name("vm", "slow")
            self.get_remote_queue_name("net", "fast")
        except Exception:
            return False
        else:
            return True

    online = property(get_online)

    @method_cache(20)
    def get_minion_online(self):
        name = self.host.hostname
        try:
            client = MyLocalClient()
            client.opts['timeout'] = 0.2
            return bool(client.cmd(name, 'test.ping')[name])
        except (KeyError, SaltClientError):
            return False

    minion_online = property(get_minion_online)

    @node_available
    @method_cache(300)
    def get_info(self):
        return self.remote_query(vm_tasks.get_info,
                                 priority='fast',
                                 default={'core_num': 0,
                                          'ram_size': 0,
                                          'architecture': ''})

    info = property(get_info)

    @property
    def allocated_ram(self):
        return (self.instance_set.aggregate(
            r=Sum('ram_size'))['r'] or 0) * 1024 * 1024

    @property
    def ram_size(self):
        warn('Use Node.info["ram_size"]', DeprecationWarning)
        return self.info['ram_size']

    @property
    def num_cores(self):
        warn('Use Node.info["core_num"]', DeprecationWarning)
        return self.info['core_num']

    STATES = {None: ({True: ('MISSING', _('missing')),
                      False: ('OFFLINE', _('offline'))}),
              False: {False: ('DISABLED', _('disabled'))},
              True: {False: ('PASSIVE', _('passive')),
                     True: ('ACTIVE', _('active'))}}

    def _get_state(self):
        """The state tuple based on online and enabled attributes.
        """
        if self.online:
            return self.STATES[self.enabled][self.schedule_enabled]
        else:
            return self.STATES[None][self.enabled]

    def get_status_display(self):
        return self._get_state()[1]

    def get_state(self):
        return self._get_state()[0]

    state = property(get_state)

    def enable(self, user=None, base_activity=None):
        raise NotImplementedError("Use activate or passivate instead.")

    @property
    @node_available
    def ram_size_with_overcommit(self):
        """Bytes of total memory including overcommit margin.
        """
        return self.ram_size * self.overcommit

    @method_cache(30)
    def get_remote_queue_name(self, queue_id, priority=None):
        """Returns the name of the remote celery queue for this node.

        Throws Exception if there is no worker on the queue.
        The result may include dead queues because of caching.
        """

        if vm_tasks.check_queue(self.host.hostname, queue_id, priority):
            queue_name = self.host.hostname + "." + queue_id
            if priority is not None:
                queue_name = queue_name + "." + priority
            self.node_online()
            return queue_name
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

    def remote_query(self, task, timeout=30, priority=None, raise_=False,
                     default=None):
        """Query the given task, and get the result.

        If the result is not ready or worker not reachable
        in timeout secs, return default value or raise a
        TimeoutError or WorkerNotFound exception.
        """
        try:
            r = task.apply_async(
                queue=self.get_remote_queue_name('vm', priority),
                expires=timeout + 60)
            return r.get(timeout=timeout)
        except (TimeoutError, WorkerNotFound):
            if raise_:
                raise
            else:
                return default

    @property
    @node_available
    @method_cache(10)
    def monitor_info(self):
        metrics = ('cpu.percent', 'memory.usage')
        prefix = 'circle.%s.' % self.host.hostname
        params = [('target', '%s%s' % (prefix, metric))
                  for metric in metrics]
        params.append(('from', '-5min'))
        params.append(('format', 'json'))

        try:
            logger.info('%s %s', settings.GRAPHITE_URL, params)
            response = requests.get(settings.GRAPHITE_URL, params=params)

            retval = {}
            for target in response.json():
                # Example:
                # {"target": "circle.szianode.cpu.usage",
                #  "datapoints": [[0.6, 1403045700], [0.5, 1403045760]
                try:
                    metric = target['target']
                    if metric.startswith(prefix):
                        metric = metric[len(prefix):]
                    else:
                        continue
                    value = target['datapoints'][-2][0]
                    retval[metric] = float(value)
                except (KeyError, IndexError, ValueError):
                    continue

            return retval
        except Exception:
            logger.exception('Unhandled exception: ')
            return self.remote_query(vm_tasks.get_node_metrics, timeout=30,
                                     priority="fast")

    @property
    @node_available
    def driver_version(self):
        return self.info.get('driver_version')

    @property
    @node_available
    def cpu_usage(self):
        return self.monitor_info.get('cpu.percent') / 100

    @property
    @node_available
    def ram_usage(self):
        return self.monitor_info.get('memory.usage') / 100

    @property
    @node_available
    def byte_ram_usage(self):
        return self.ram_usage * self.ram_size

    def get_status_icon(self):
        return {
            'DISABLED': 'fa-times-circle-o',
            'OFFLINE': 'fa-times-circle',
            'MISSING': 'fa-warning',
            'PASSIVE': 'fa-play-circle-o',
            'ACTIVE': 'fa-play-circle'}.get(self.get_state(),
                                            'fa-question-circle')

    def get_status_label(self):
        return {
            'OFFLINE': 'label-warning',
            'DISABLED': 'label-danger',
            'MISSING': 'label-danger',
            'ACTIVE': 'label-success',
            'PASSIVE': 'label-warning',
        }.get(self.get_state(), 'label-danger')

    @node_available
    def update_vm_states(self):
        """Update state of Instances running on this Node.

        Query state of all libvirt domains, and notify Instances by their
        vm_state_changed hook.
        """
        domains = {}
        domain_list = self.remote_query(vm_tasks.list_domains_info, timeout=5,
                                        priority="fast")
        if domain_list is None:
            logger.info("Monitoring failed at: %s", self.name)
            return
        for i in domain_list:
            # [{'name': 'cloud-1234', 'state': 'RUNNING', ...}, ...]
            try:
                id = int(i['name'].split('-')[1])
            except Exception:
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
                self.instance_set.get(id=i['id']).vm_state_changed(
                    'STOPPED', None)
            else:
                if d != i['state']:
                    logger.info('Node %s update: instance %s state changed '
                                '(libvirt: %s, db: %s)',
                                self, i['id'], d, i['state'])
                    self.instance_set.get(id=i['id']).vm_state_changed(d)

                del domains[i['id']]
        for id, state in domains.iteritems():
            from .instance import Instance
            logger.error('Node %s update: domain %s in libvirt but not in db.',
                         self, id)
            Instance.objects.get(id=id).vm_state_changed(state, self)

    @classmethod
    def get_state_count(cls, online, enabled):
        return len([1 for i in
                    cls.objects.filter(enabled=enabled).select_related('host')
                    if i.online == online])

    @permalink
    def get_absolute_url(self):
        return ('dashboard.views.node-detail', None, {'pk': self.id})

    def save(self, *args, **kwargs):
        if not self.enabled:
            self.schedule_enabled = False
        super(Node, self).save(*args, **kwargs)

    @property
    def metric_prefix(self):
        return 'circle.%s' % self.host.hostname
