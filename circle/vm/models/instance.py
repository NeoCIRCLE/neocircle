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
from contextlib import contextmanager
from datetime import timedelta
from functools import partial
from importlib import import_module
from logging import getLogger
from warnings import warn

import django.conf
from django.contrib.auth.models import User
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.db.models import (BooleanField, CharField, DateTimeField,
                              IntegerField, ForeignKey, Manager,
                              ManyToManyField, permalink, SET_NULL, TextField)
from django.db import IntegrityError
from django.dispatch import Signal
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _, ugettext_noop

from model_utils import Choices
from model_utils.managers import QueryManager
from model_utils.models import TimeStampedModel, StatusModel
from taggit.managers import TaggableManager

from acl.models import AclBase
from common.models import (
    activitycontextimpl, create_readable, HumanReadableException,
)
from common.operations import OperatedMixin
from ..tasks import agent_tasks
from .activity import (ActivityInProgressError, InstanceActivity)
from .common import BaseResourceConfigModel, Lease
from .network import Interface
from .node import Node, Trait

logger = getLogger(__name__)
pre_state_changed = Signal(providing_args=["new_state"])
post_state_changed = Signal(providing_args=["new_state"])
pwgen = partial(User.objects.make_random_password,
                allowed_chars='abcdefghijklmnopqrstuvwx'
                              'ABCDEFGHIJKLMNOPQRSTUVWX123456789')
scheduler = import_module(name=django.conf.settings.VM_SCHEDULER)

ACCESS_PROTOCOLS = django.conf.settings.VM_ACCESS_PROTOCOLS
ACCESS_METHODS = [(key, name) for key, (name, port, transport)
                  in ACCESS_PROTOCOLS.iteritems()]


def find_unused_port(port_range, used_ports=[]):
    """Find an unused port in the specified range.

    The list of used ports can be specified optionally.

    :param port_range: a tuple representing a port range (w/ exclusive end)
                       e.g. (6000, 7000) represents ports 6000 through 6999
    """
    ports = xrange(*port_range)
    used = set(used_ports)
    unused = (port for port in ports if port not in used)
    return next(unused, None)  # first or None


def find_unused_vnc_port():
    port = find_unused_port(
        port_range=django.conf.settings.VNC_PORT_RANGE,
        used_ports=Instance.objects.values_list('vnc_port', flat=True))

    if port is None:
        raise Exception("No unused port could be found for VNC.")
    else:
        return port


class VirtualMachineDescModel(BaseResourceConfigModel):

    """Abstract base for virtual machine describing models.
    """
    access_method = CharField(max_length=10, choices=ACCESS_METHODS,
                              verbose_name=_('access method'),
                              help_text=_('Primary remote access method.'))
    boot_menu = BooleanField(verbose_name=_('boot menu'), default=False,
                             help_text=_(
                                 'Show boot device selection menu on boot.'))
    lease = ForeignKey(Lease, help_text=_("Preferred expiration periods."),
                       verbose_name=_("Lease"))
    raw_data = TextField(verbose_name=_('raw_data'), blank=True, help_text=_(
        'Additional libvirt domain parameters in XML format.'))
    req_traits = ManyToManyField(Trait, blank=True,
                                 help_text=_("A set of traits required for a "
                                             "node to declare to be suitable "
                                             "for hosting the VM."),
                                 verbose_name=_("required traits"))
    system = TextField(verbose_name=_('operating system'),
                       help_text=(_('Name of operating system in format like '
                                    '"Ubuntu 12.04 LTS Desktop amd64".')))
    tags = TaggableManager(blank=True, verbose_name=_("tags"))
    has_agent = BooleanField(verbose_name=_('has agent'), default=True,
                             help_text=_(
                                 'If the machine has agent installed, and '
                                 'the manager should wait for its start.'))

    class Meta:
        abstract = True


class InstanceTemplate(AclBase, VirtualMachineDescModel, TimeStampedModel):

    """Virtual machine template.
    """
    ACL_LEVELS = (
        ('user', _('user')),          # see all details
        ('operator', _('operator')),
        ('owner', _('owner')),        # superuser, can delete, delegate perms
    )
    name = CharField(max_length=100, verbose_name=_('name'),
                     help_text=_('Human readable name of template.'))
    description = TextField(verbose_name=_('description'), blank=True)
    parent = ForeignKey('self', null=True, blank=True,
                        verbose_name=_('parent template'),
                        on_delete=SET_NULL,
                        help_text=_('Template which this one is derived of.'))
    disks = ManyToManyField('storage.Disk', verbose_name=_('disks'),
                            related_name='template_set',
                            help_text=_('Disks which are to be mounted.'))
    owner = ForeignKey(User)

    class Meta:
        app_label = 'vm'
        db_table = 'vm_instancetemplate'
        ordering = ('name', )
        permissions = (
            ('create_template', _('Can create an instance template.')),
            ('create_base_template',
             _('Can create an instance template (base).')),
            ('change_template_resources',
             _('Can change resources of a template.')),
        )
        verbose_name = _('template')
        verbose_name_plural = _('templates')

    def __unicode__(self):
        return self.name

    @property
    def running_instances(self):
        """The number of running instances of the template.
        """
        return sum(1 for i in self.instance_set.all() if i.is_running)

    @property
    def os_type(self):
        """The type of the template's operating system.
        """
        if self.access_method == 'rdp':
            return 'windows'
        else:
            return 'linux'

    @property
    def is_ready(self):
        return all(disk.is_ready for disk in self.disks)

    def save(self, *args, **kwargs):
        is_new = getattr(self, "pk", None) is None
        super(InstanceTemplate, self).save(*args, **kwargs)
        if is_new:
            self.set_level(self.owner, 'owner')

    @permalink
    def get_absolute_url(self):
        return ('dashboard.views.template-detail', None, {'pk': self.pk})

    def remove_disk(self, disk, **kwargs):
        self.disks.remove(disk)

    def destroy_disks(self):
        """Destroy all associated disks.
        """
        for disk in self.disks.all():
            disk.destroy()

    def get_running_instances(self):
        return Instance.active.filter(template=self, status="RUNNING")

    @property
    def metric_prefix(self):
        return 'template.%d' % self.pk


class Instance(AclBase, VirtualMachineDescModel, StatusModel, OperatedMixin,
               TimeStampedModel):

    """Virtual machine instance.
    """
    ACL_LEVELS = (
        ('user', _('user')),          # see all details
        ('operator', _('operator')),  # console, networking, change state
        ('owner', _('owner')),        # superuser, can delete, delegate perms
    )
    STATUS = Choices(
        ('NOSTATE', _('no state')),
        ('RUNNING', _('running')),
        ('STOPPED', _('stopped')),
        ('SUSPENDED', _('suspended')),
        ('ERROR', _('error')),
        ('PENDING', _('pending')),
        ('DESTROYED', _('destroyed')),
    )
    name = CharField(blank=True, max_length=100, verbose_name=_('name'),
                     help_text=_("Human readable name of instance."))
    description = TextField(blank=True, verbose_name=_('description'))
    template = ForeignKey(InstanceTemplate, blank=True, null=True,
                          related_name='instance_set', on_delete=SET_NULL,
                          help_text=_("Template the instance derives from."),
                          verbose_name=_('template'))
    pw = CharField(help_text=_("Original password of the instance."),
                   max_length=20, verbose_name=_('password'))
    time_of_suspend = DateTimeField(blank=True, default=None, null=True,
                                    verbose_name=_('time of suspend'),
                                    help_text=_("Proposed time of automatic "
                                                "suspension."))
    time_of_delete = DateTimeField(blank=True, default=None, null=True,
                                   verbose_name=_('time of delete'),
                                   help_text=_("Proposed time of automatic "
                                               "deletion."))
    node = ForeignKey(Node, blank=True, null=True,
                      related_name='instance_set',
                      help_text=_("Current hypervisor of this instance."),
                      verbose_name=_('host node'))
    disks = ManyToManyField('storage.Disk', related_name='instance_set',
                            help_text=_("Set of mounted disks."),
                            verbose_name=_('disks'))
    vnc_port = IntegerField(blank=True, default=None, null=True,
                            help_text=_("TCP port where VNC console listens."),
                            unique=True, verbose_name=_('vnc_port'))
    is_base = BooleanField(default=False)
    owner = ForeignKey(User)
    destroyed_at = DateTimeField(blank=True, null=True,
                                 help_text=_("The virtual machine's time of "
                                             "destruction."))
    objects = Manager()
    active = QueryManager(destroyed_at=None)

    class Meta:
        app_label = 'vm'
        db_table = 'vm_instance'
        ordering = ('pk', )
        permissions = (
            ('access_console', _('Can access the graphical console of a VM.')),
            ('change_resources', _('Can change resources of a running VM.')),
            ('set_resources', _('Can change resources of a new VM.')),
            ('create_vm', _('Can create a new VM.')),
            ('redeploy', _('Can redeploy a VM.')),
            ('config_ports', _('Can configure port forwards.')),
            ('recover', _('Can recover a destroyed VM.')),
            ('emergency_change_state', _('Can change VM state to NOSTATE.')),
        )
        verbose_name = _('instance')
        verbose_name_plural = _('instances')

    class InstanceError(HumanReadableException):

        def __init__(self, instance, params=None, level=None, **kwargs):
            kwargs.update(params or {})
            self.instance = kwargs["instance"] = instance
            super(Instance.InstanceError, self).__init__(
                level, self.message, self.message, kwargs)

    class InstanceDestroyedError(InstanceError):
        message = ugettext_noop(
            "Instance %(instance)s has already been destroyed.")

    class NoAgentError(InstanceError):
        message = ugettext_noop(
            "No agent software is running on instance %(instance)s.")

    class WrongStateError(InstanceError):
        message = ugettext_noop(
            "Current state (%(state)s) of instance %(instance)s is "
            "inappropriate for the invoked operation.")

        def __init__(self, instance, params=None, **kwargs):
            super(Instance.WrongStateError, self).__init__(
                instance, params, state=instance.status)

    def __unicode__(self):
        parts = (self.name, "(" + str(self.id) + ")")
        return " ".join(s for s in parts if s != "")

    @property
    def is_console_available(self):
        return self.is_running

    @property
    def is_running(self):
        """Check if VM is in running state.
        """
        return self.status == 'RUNNING'

    @property
    def state(self):
        warn('Use Instance.status (or get_status_display) instead.',
             DeprecationWarning)
        return self.status

    def _update_status(self):
        """Set the proper status of the instance to Instance.status.
        """
        old = self.status
        self.status = self._compute_status()
        if old != self.status:
            logger.info('Status of Instance#%d changed to %s',
                        self.pk, self.status)
            self.save(update_fields=('status', ))

    def _compute_status(self):
        """Return the proper status of the instance based on activities.
        """
        # check special cases
        if self.activity_log.filter(activity_code__endswith='migrate',
                                    finished__isnull=True).exists():
            return 'MIGRATING'

        # <<< add checks for special cases before this

        # default case
        acts = self.activity_log.filter(finished__isnull=False,
                                        resultant_state__isnull=False
                                        ).order_by('-finished')[:1]
        try:
            act = acts[0]
        except IndexError:
            return 'NOSTATE'
        else:
            return act.resultant_state

    @classmethod
    def create(cls, params, disks, networks, req_traits, tags):
        """ Create new Instance object.
        """

        # permission check
        for network in networks:
            if not network.vlan.has_level(params['owner'], 'user'):
                raise PermissionDenied()

        # create instance and do additional setup
        inst = cls(**params)

        # save instance
        inst.full_clean()
        inst.save()
        inst.set_level(inst.owner, 'owner')

        def __on_commit(activity):
            activity.resultant_state = 'PENDING'

        with inst.activity(code_suffix='create',
                           readable_name=ugettext_noop("create instance"),
                           on_commit=__on_commit, user=inst.owner) as act:
            # create related entities
            inst.disks.add(*[disk.get_exclusive() for disk in disks])

            for net in networks:
                Interface.create(instance=inst, vlan=net.vlan,
                                 owner=inst.owner, managed=net.managed,
                                 base_activity=act)

            inst.req_traits.add(*req_traits)
            inst.tags.add(*tags)

            return inst

    @classmethod
    def create_from_template(cls, template, owner, disks=None, networks=None,
                             req_traits=None, tags=None, **kwargs):
        """Create a new instance based on an InstanceTemplate.

        Can also specify parameters as keyword arguments which should override
        template settings.
        """
        insts = cls.mass_create_from_template(template, owner, disks=disks,
                                              networks=networks, tags=tags,
                                              req_traits=req_traits, **kwargs)
        return insts[0]

    @classmethod
    def mass_create_from_template(cls, template, owner, amount=1, disks=None,
                                  networks=None, req_traits=None, tags=None,
                                  **kwargs):
        """Mass-create new instances based on an InstanceTemplate.

        Can also specify parameters as keyword arguments which should override
        template settings.
        """
        disks = template.disks.all() if disks is None else disks

        networks = (template.interface_set.all() if networks is None
                    else networks)

        req_traits = (template.req_traits.all() if req_traits is None
                      else req_traits)

        tags = template.tags.all() if tags is None else tags

        # prepare parameters
        common_fields = ['name', 'description', 'num_cores', 'ram_size',
                         'max_ram_size', 'arch', 'priority', 'boot_menu',
                         'raw_data', 'lease', 'access_method', 'system',
                         'has_agent']
        params = dict(template=template, owner=owner, pw=pwgen())
        params.update([(f, getattr(template, f)) for f in common_fields])
        params.update(kwargs)  # override defaults w/ user supplied values

        if amount > 1 and '%d' not in params['name']:
            params['name'] += ' %d'

        customized_params = (dict(params,
                                  name=params['name'].replace('%d', str(i)))
                             for i in xrange(amount))
        return [cls.create(cps, disks, networks, req_traits, tags)
                for cps in customized_params]

    def clean(self, *args, **kwargs):
        self.time_of_suspend, self.time_of_delete = self.get_renew_times()
        super(Instance, self).clean(*args, **kwargs)

    def vm_state_changed(self, new_state, new_node=False):
        if new_node is False:  # None would be a valid value
            new_node = self.node
        # log state change

        if new_node:
            msg = ugettext_noop("vm state changed to %(state)s on %(node)s")
        else:
            msg = ugettext_noop("vm state changed to %(state)s")

        try:
            act = InstanceActivity.create(
                code_suffix='vm_state_changed',
                readable_name=create_readable(msg, state=new_state,
                                              node=new_node),
                instance=self)
        except ActivityInProgressError:
            pass  # discard state change if another activity is in progress.
        else:
            if self.node != new_node:
                self.node = new_node
                self.save()
            act.finished = act.started
            act.resultant_state = new_state
            act.succeeded = True
            act.save()

    @permalink
    def get_absolute_url(self):
        return ('dashboard.views.detail', None, {'pk': self.id})

    @property
    def vm_name(self):
        """Name of the VM instance.

        This is a unique identifier as opposed to the 'name' attribute, which
        is just for display.
        """
        return 'cloud-' + str(self.id)

    @property
    def mem_dump(self):
        """Return the path and datastore for the memory dump.

        It is always on the first hard drive storage named cloud-<id>.dump
        """
        try:
            datastore = self.disks.all()[0].datastore
        except IndexError:
            from storage.models import DataStore
            datastore = DataStore.objects.get()

        path = datastore.path + '/' + self.vm_name + '.dump'
        return {'datastore': datastore, 'path': path}

    @property
    def primary_host(self):
        interfaces = self.interface_set.select_related('host')
        hosts = [i.host for i in interfaces if i.host]
        if not hosts:
            return None
        hs = [h for h in hosts if h.ipv6]
        if hs:
            return hs[0]
        hs = [h for h in hosts if not h.shared_ip]
        if hs:
            return hs[0]
        return hosts[0]

    @property
    def ipv4(self):
        """Primary IPv4 address of the instance.
        """
        # return self.primary_host.ipv4 if self.primary_host else None
        for i in self.interface_set.all():
            if i.host:
                return i.host.ipv4
        return None

    @property
    def ipv6(self):
        """Primary IPv6 address of the instance.
        """
        return self.primary_host.ipv6 if self.primary_host else None

    @property
    def mac(self):
        """Primary MAC address of the instance.
        """
        return self.primary_host.mac if self.primary_host else None

    @property
    def os_type(self):
        """Get the type of the instance's operating system.
        """
        if self.template is None:
            return "unknown"
        else:
            return self.template.os_type

    @property
    def waiting(self):
        """Indicates whether the instance's waiting for an operation to finish.
        """
        return self.activity_log.filter(finished__isnull=True).exists()

    def get_connect_port(self, use_ipv6=False):
        """Get public port number for default access method.
        """
        port, proto = ACCESS_PROTOCOLS[self.access_method][1:3]
        if self.primary_host:
            endpoints = self.primary_host.get_public_endpoints(port, proto)
            endpoint = endpoints['ipv6'] if use_ipv6 else endpoints['ipv4']
            return endpoint[1] if endpoint else None
        else:
            return None

    def get_connect_host(self, use_ipv6=False):
        """Get public hostname.
        """
        if not self.primary_host:
            return None
        proto = 'ipv6' if use_ipv6 else 'ipv4'
        return self.primary_host.get_hostname(proto=proto)

    def get_connect_command(self, use_ipv6=False):
        """Returns a formatted connect string.
        """
        try:
            port = self.get_connect_port(use_ipv6=use_ipv6)
            host = self.get_connect_host(use_ipv6=use_ipv6)
            proto = self.access_method
            if proto == 'rdp':
                return 'rdesktop %(host)s:%(port)d -u cloud -p %(pw)s' % {
                    'port': port, 'proto': proto, 'pw': self.pw,
                    'host': host}
            elif proto == 'ssh':
                return ('sshpass -p %(pw)s ssh -o StrictHostKeyChecking=no '
                        'cloud@%(host)s -p %(port)d') % {
                    'port': port, 'proto': proto, 'pw': self.pw,
                    'host': host}
        except:
            return

    def get_connect_uri(self, use_ipv6=False):
        """Get access parameters in URI format.
        """
        try:
            port = self.get_connect_port(use_ipv6=use_ipv6)
            host = self.get_connect_host(use_ipv6=use_ipv6)
            proto = self.access_method
            return ('circle:%(proto)s:cloud:%(pw)s:%(host)s:%(port)d' %
                    {'port': port, 'proto': proto, 'pw': self.pw,
                     'host': host})
        except:
            return

    @property
    def short_hostname(self):
        try:
            return self.primary_host.hostname
        except AttributeError:
            return self.vm_name

    def get_vm_desc(self):
        """Serialize Instance object to vmdriver.
        """
        return {
            'name': self.vm_name,
            'vcpu': self.num_cores,
            'memory': int(self.ram_size) * 1024,  # convert from MiB to KiB
            'memory_max': int(self.max_ram_size) * 1024,  # convert MiB to KiB
            'cpu_share': self.priority,
            'arch': self.arch,
            'boot_menu': self.boot_menu,
            'network_list': [n.get_vmnetwork_desc()
                             for n in self.interface_set.all()],
            'disk_list': [d.get_vmdisk_desc() for d in self.disks.all()],
            'graphics': {
                'type': 'vnc',
                'listen': '0.0.0.0',
                'passwd': '',
                'port': self.vnc_port
            },
            'boot_token': signing.dumps(self.id, salt='activate'),
            'raw_data': "" if not self.raw_data else self.raw_data
        }

    def get_remote_queue_name(self, queue_id, priority=None):
        """Get the remote worker queue name of this instance with the specified
           queue ID.
        """
        if self.node:
            return self.node.get_remote_queue_name(queue_id, priority)
        else:
            raise Node.DoesNotExist()

    def _is_notified_about_expiration(self):
        last_activity = self.activity_log.latest('pk')
        return (last_activity.activity_code ==
                'vm.Instance.notification_about_expiration')

    def notify_owners_about_expiration(self, again=False):
        """Notify owners about vm expiring soon if they aren't already.

        :param again: Notify already notified owners.
        """

        notification_msg = ugettext_noop(
            'Your instance <a href="%(url)s">%(instance)s</a> is going to '
            'expire. It will be suspended at %(suspend)s and destroyed at '
            '%(delete)s. Please, either <a href="%(token)s">renew</a> '
            'or <a href="%(url)s">destroy</a> it now.')

        if not again and self._is_notified_about_expiration():
            return False
        success, failed = [], []

        def on_commit(act):
            if failed:
                act.result = create_readable(ugettext_noop(
                    "%(failed)s notifications failed and %(success) succeeded."
                    " Failed ones are: %(faileds)s."), ugettext_noop(
                    "%(failed)s notifications failed and %(success) succeeded."
                    " Failed ones are: %(faileds_ex)s."),
                    failed=len(failed), success=len(success),
                    faileds=", ".join(a for a, e in failed),
                    faileds_ex=", ".join("%s (%s)" % (a, unicode(e))
                                         for a, e in failed))
            else:
                act.result = create_readable(ugettext_noop(
                    "%(success)s notifications succeeded."),
                    success=len(success), successes=success)

        with self.activity('notification_about_expiration',
                           readable_name=ugettext_noop(
                               "notify owner about expiration"),
                           on_commit=on_commit, concurrency_check=False):
            from dashboard.views import VmRenewView, absolute_url
            level = self.get_level_object("owner")
            for u, ulevel in self.get_users_with_level(level__pk=level.pk):
                try:
                    token = VmRenewView.get_token_url(self, u)
                    u.profile.notify(
                        ugettext_noop('%(instance)s expiring soon'),
                        notification_msg, url=self.get_absolute_url(),
                        instance=self, suspend=self.time_of_suspend,
                        token=token, delete=self.time_of_delete)
                except Exception as e:
                    failed.append((u, e))
                else:
                    success.append(u)
            if self.status == "RUNNING":
                token = absolute_url(
                    VmRenewView.get_token_url(self, self.owner))
                queue = self.get_remote_queue_name("agent")
                agent_tasks.send_expiration.apply_async(
                    queue=queue, args=(self.vm_name, token))
        return True

    def is_expiring(self, threshold=0.1):
        """Returns if an instance will expire soon.

        Soon means that the time of suspend or delete comes in 10% of the
        interval what the Lease allows. This rate is configurable with the
        only parameter, threshold (0.1 = 10% by default).
        """
        return (self._is_suspend_expiring(threshold) or
                self._is_delete_expiring(threshold))

    def _is_suspend_expiring(self, threshold=0.1):
        interval = self.lease.suspend_interval
        if (self.status != "SUSPENDED" and
                self.time_of_suspend is not None and interval is not None):
            limit = timezone.now() + timedelta(seconds=(
                threshold * self.lease.suspend_interval.total_seconds()))
            return limit > self.time_of_suspend
        else:
            return False

    def _is_delete_expiring(self, threshold=0.1):
        interval = self.lease.delete_interval
        if self.time_of_delete is not None and interval is not None:
            limit = timezone.now() + timedelta(seconds=(
                threshold * self.lease.delete_interval.total_seconds()))
            return limit > self.time_of_delete
        else:
            return False

    def get_renew_times(self, lease=None):
        """Returns new suspend and delete times if renew would be called.
        """
        if lease is None:
            lease = self.lease
        return (
            timezone.now() + lease.suspend_interval,
            timezone.now() + lease.delete_interval)

    def select_node(self):
        """Returns the node the VM should be deployed or migrated to.
        """
        return scheduler.select_node(self, Node.objects.all())

    def destroy_disks(self):
        """Destroy all associated disks.
        """
        for disk in self.disks.all():
            disk.destroy()

    def deploy_net(self):
        """Deploy all associated network interfaces.
        """
        for net in self.interface_set.all():
            net.deploy()

    def destroy_net(self):
        """Destroy all associated network interfaces.
        """
        for net in self.interface_set.all():
            net.destroy()

    def shutdown_net(self):
        """Shutdown all associated network interfaces.
        """
        for net in self.interface_set.all():
            net.shutdown()

    def allocate_node(self):
        if self.node is None:
            self.node = self.select_node()
            self.save()
            return self.node

    def yield_node(self):
        if self.node is not None:
            self.node = None
            self.save()

    def allocate_vnc_port(self):
        if self.vnc_port is None:
            while True:
                try:
                    self.vnc_port = find_unused_vnc_port()
                    self.save()
                except IntegrityError:
                    # Another thread took this port get another one
                    logger.debug("Port %s is in use.", self.vnc_port)
                    pass
                else:
                    break

    def yield_vnc_port(self):
        if self.vnc_port is not None:
            self.vnc_port = None
            self.save()

    def get_status_icon(self):
        return {
            'NOSTATE': 'fa-rocket',
            'RUNNING': 'fa-play',
            'STOPPED': 'fa-stop',
            'SUSPENDED': 'fa-pause',
            'ERROR': 'fa-warning',
            'PENDING': 'fa-rocket',
            'DESTROYED': 'fa-trash-o',
            'MIGRATING': 'fa-truck migrating-icon'
        }.get(self.status, 'fa-question')

    def get_activities(self, user=None):
        acts = (self.activity_log.filter(parent=None).
                order_by('-started').
                select_related('user').prefetch_related('children'))
        # Check latest activity for percentage
        for i in acts:
            if i.has_percentage():
                i.has_percent = True
                i.percentage = i.get_percentage()
        if user is not None:
            for i in acts:
                i.is_abortable_for_user = partial(i.is_abortable_for,
                                                  user=user)
        return acts

    def get_merged_activities(self, user=None):
        whitelist = ("create_disk", "download_disk", "remove_disk",
                     "add_port", "remove_port",
                     "add_interface", "remove_interface")
        acts = self.get_activities(user)
        merged_acts = []
        latest = None

        for a in acts:
            if (latest == a.activity_code and
                    merged_acts[-1].result_data == a.result_data and
                    a.finished and merged_acts[-1].finished and
                    a.user == merged_acts[-1].user and
                    (merged_acts[-1].finished - a.finished).days < 7 and
                    not a.activity_code.endswith(whitelist)):
                merged_acts[-1].times += 1
            else:
                merged_acts.append(a)
                merged_acts[-1].times = 1
            latest = a.activity_code

        return merged_acts

    def get_latest_activity_in_progress(self):
        try:
            return InstanceActivity.objects.filter(
                instance=self, succeeded=None, parent=None).latest("started")
        except InstanceActivity.DoesNotExist:
            return None

    def is_in_status_change(self):
        latest = self.get_latest_activity_in_progress()
        return (latest and latest.resultant_state is not None and
                self.status != latest.resultant_state)

    @property
    def metric_prefix(self):
        return 'vm.%s' % self.vm_name

    @contextmanager
    def activity(self, code_suffix, readable_name, on_abort=None,
                 on_commit=None, task_uuid=None, user=None,
                 concurrency_check=True, resultant_state=None):
        """Create a transactional context for an instance activity.
        """
        if not readable_name:
            warn("Set readable_name", stacklevel=3)
        act = InstanceActivity.create(
            code_suffix=code_suffix, instance=self, task_uuid=task_uuid,
            user=user, concurrency_check=concurrency_check,
            readable_name=readable_name, resultant_state=resultant_state)
        return activitycontextimpl(act, on_abort=on_abort, on_commit=on_commit)
