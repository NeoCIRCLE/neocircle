from datetime import timedelta
from importlib import import_module
import logging

import django.conf
from django.contrib.auth.models import User
from django.db.models import (Model, ForeignKey, ManyToManyField, IntegerField,
                              DateTimeField, BooleanField, TextField,
                              CharField, permalink)
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from netaddr import EUI

from . import tasks
from firewall.models import Vlan, Host
from manager import vm_manager
from storage.models import Disk


logger = logging.getLogger(__name__)
pwgen = User.objects.make_random_password
scheduler = import_module(name=django.conf.settings.VM_SCHEDULER)
ACCESS_PROTOCOLS = django.conf.settings.VM_ACCESS_PROTOCOLS
ACCESS_METHODS = [(key, name) for key, (name, port, transport)
                  in ACCESS_PROTOCOLS.iteritems()]
ARCHITECTURES = (('x86_64', 'x86-64 (64 bit)'),
                 ('i686', 'x86 (32 bit)'))


class BaseResourceConfigModel(Model):

    """Abstract base class for models with base resource configuration
       parameters.
    """
    num_cores = IntegerField(verbose_name=_('number of cores'),
                             help_text=_('Number of virtual CPU cores '
                                         'available to the virtual machine.'))
    ram_size = IntegerField(verbose_name=_('RAM size'),
                            help_text=_('Mebibytes of memory.'))
    max_ram_size = IntegerField(verbose_name=_('maximal RAM size'),
                                help_text=_('Upper memory size limit '
                                            'for balloning.'))
    arch = CharField(max_length=10, verbose_name=_('architecture'),
                     choices=ARCHITECTURES)
    priority = IntegerField(verbose_name=_('priority'),
                            help_text=_('CPU priority.'))
    boot_menu = BooleanField(verbose_name=_('boot menu'), default=False,
                             help_text=_(
                                 'Show boot device selection menu on boot.'))
    raw_data = TextField(verbose_name=_('raw_data'), blank=True, help_text=_(
        'Additional libvirt domain parameters in XML format.'))

    class Meta:
        abstract = True


class NamedBaseResourceConfig(BaseResourceConfigModel, TimeStampedModel):

    """Pre-created, named base resource configurations.
    """
    name = CharField(max_length=50, unique=True,
                     verbose_name=_('name'), help_text=
                     _('Name of base resource configuration.'))

    def __unicode__(self):
        return self.name


class Node(TimeStampedModel):

    """A VM host machine, a hypervisor.
    """
    name = CharField(max_length=50, unique=True,
                     verbose_name=_('name'),
                     help_text=_('Human readable name of node.'))
    num_cores = IntegerField(verbose_name=_('number of cores'),
                             help_text=_('Number of CPU threads '
                                         'available to the virtual machines.'))
    ram_size = IntegerField(verbose_name=_('RAM size'),
                            help_text=_('Mebibytes of memory.'))
    priority = IntegerField(verbose_name=_('priority'),
                            help_text=_('Node usage priority.'))
    host = ForeignKey(Host, verbose_name=_('host'),
                      help_text=_('Host in firewall.'))
    enabled = BooleanField(verbose_name=_('enabled'), default=False,
                           help_text=_('Indicates whether the node can '
                                       'be used for hosting.'))

    class Meta:
        permissions = ()

    @property
    def online(self):
        """Indicates whether the node is connected and functional.
        """
        pass  # TODO implement check

    def __unicode__(self):
        return self.name


class NodeActivity(TimeStampedModel):
    activity_code = CharField(verbose_name=_('activity code'),
                              max_length=100)  # TODO
    task_uuid = CharField(verbose_name=_('task_uuid'), blank=True,
                          max_length=50, null=True, unique=True, help_text=_(
                              'Celery task unique identifier.'))
    node = ForeignKey(Node, verbose_name=_('node'),
                      related_name='activity_log',
                      help_text=_('Node this activity works on.'))
    user = ForeignKey(User, verbose_name=_('user'), blank=True, null=True,
                      help_text=_('The person who started this activity.'))
    started = DateTimeField(verbose_name=_('started at'),
                            blank=True, null=True,
                            help_text=_('Time of activity initiation.'))
    finished = DateTimeField(verbose_name=_('finished at'),
                             blank=True, null=True,
                             help_text=_('Time of activity finalization.'))
    result = TextField(verbose_name=_('result'), blank=True, null=True,
                       help_text=_('Human readable result of activity.'))
    status = CharField(verbose_name=_('status'), default='PENDING',
                       max_length=50, help_text=_('Actual state of activity'))


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


class InstanceTemplate(BaseResourceConfigModel, TimeStampedModel):

    """Virtual machine template.

    Every template has:
      * a name and a description
      * an optional parent template
      * state of the template
      * an OS name/description
      * a method of access to the system
      * default values of base resource configuration
      * list of attached images
      * set of interfaces
      * lease times (suspension & deletion)
      * time of creation and last modification
    """
    STATES = [('NEW', _('new')),        # template has just been created
              ('SAVING', _('saving')),  # changes are being saved
              ('READY', _('ready'))]    # template is ready for instantiation
    name = CharField(max_length=100, unique=True,
                     verbose_name=_('name'),
                     help_text=_('Human readable name of template.'))
    description = TextField(verbose_name=_('description'), blank=True)
    parent = ForeignKey('self', null=True, blank=True,
                        verbose_name=_('parent template'),
                        help_text=_('Template which this one is derived of.'))
    system = TextField(verbose_name=_('operating system'),
                       blank=True,
                       help_text=(_('Name of operating system in '
                                    'format like "%s".') %
                                  'Ubuntu 12.04 LTS Desktop amd64'))
    access_method = CharField(max_length=10, choices=ACCESS_METHODS,
                              verbose_name=_('access method'),
                              help_text=_('Primary remote access method.'))
    state = CharField(max_length=10, choices=STATES, default='NEW')
    disks = ManyToManyField(Disk, verbose_name=_('disks'),
                            related_name='template_set',
                            help_text=_('Disks which are to be mounted.'))
    lease = ForeignKey(Lease, related_name='template_set',
                       verbose_name=_('lease'),
                       help_text=_('Expiration times.'))

    class Meta:
        ordering = ['name', ]
        permissions = ()
        verbose_name = _('template')
        verbose_name_plural = _('templates')

    def __unicode__(self):
        return self.name

    def running_instances(self):
        """Returns the number of running instances of the template.
        """
        return self.instance_set.filter(state='RUNNING').count()

    @property
    def os_type(self):
        """Get the type of the template's operating system.
        """
        if self.access_method == 'rdp':
            return 'win'
        else:
            return 'linux'


class InterfaceTemplate(Model):

    """Network interface template for an instance template.

    If the interface is managed, a host will be created for it.
    """
    vlan = ForeignKey(Vlan, verbose_name=_('vlan'),
                      help_text=_('Network the interface belongs to.'))
    managed = BooleanField(verbose_name=_('managed'), default=True,
                           help_text=_('If a firewall host (i.e. IP address '
                                       'association) should be generated.'))
    template = ForeignKey(InstanceTemplate, verbose_name=_('template'),
                          related_name='interface_set',
                          help_text=_())

    class Meta:
        permissions = ()
        verbose_name = _('interface template')
        verbose_name_plural = _('interface templates')


class Instance(BaseResourceConfigModel, TimeStampedModel):

    """Virtual machine instance.

    Every instance has:
      * a name and a description
      * an optional parent template
      * associated share
      * a generated password for login authentication
      * time of deletion and time of suspension
      * lease times (suspension & deletion)
      * last boot timestamp
      * host node
      * current state (libvirt domain state)
      * time of creation and last modification
      * base resource configuration values
      * owner and privilege information
    """
    STATES = [('NOSTATE', _('nostate')),
              ('RUNNING', _('running')),
              ('BLOCKED', _('blocked')),
              ('PAUSED', _('paused')),
              ('SHUTDOWN', _('shutdown')),
              ('SHUTOFF', _('shutoff')),
              ('CRASHED', _('crashed')),
              ('PMSUSPENDED', _('pmsuspended'))]  # libvirt domain states
    name = CharField(blank=True, max_length=100, verbose_name=_('name'),
                     help_text=_('Human readable name of instance.'))
    description = TextField(blank=True, verbose_name=_('description'))
    template = ForeignKey(InstanceTemplate, blank=True, null=True,
                          related_name='instance_set',
                          help_text=_('Template the instance derives from.'),
                          verbose_name=_('template'))
    pw = CharField(help_text=_('Original password of the instance.'),
                   max_length=20, verbose_name=_('password'))
    time_of_suspend = DateTimeField(blank=True, default=None, null=True,
                                    verbose_name=_('time of suspend'),
                                    help_text=_('Proposed time of automatic '
                                                'suspension.'))
    time_of_delete = DateTimeField(blank=True, default=None, null=True,
                                   verbose_name=_('time of delete'),
                                   help_text=_('Proposed time of automatic '
                                               'suspension.'))
    active_since = DateTimeField(blank=True, null=True,
                                 help_text=_('Time stamp of successful '
                                             'boot report.'),
                                 verbose_name=_('active since'))
    node = ForeignKey(Node, blank=True, null=True,
                      related_name='instance_set',
                      help_text=_('Current hypervisor of this instance.'),
                      verbose_name=_('host node'))
    state = CharField(choices=STATES, default='NOSTATE', max_length=20)
    disks = ManyToManyField(Disk, related_name='instance_set',
                            help_text=_('Set of mounted disks.'),
                            verbose_name=_('disks'))
    lease = ForeignKey(Lease, help_text=_('Preferred expiration periods.'))
    access_method = CharField(max_length=10, choices=ACCESS_METHODS,
                              help_text=_('Primary remote access method.'),
                              verbose_name=_('access method'))
    vnc_port = IntegerField(verbose_name=_('vnc_port'),
                            help_text=_('TCP port where VNC console listens.'))
    owner = ForeignKey(User)

    class Meta:
        ordering = ['pk', ]
        permissions = ()
        verbose_name = _('instance')
        verbose_name_plural = _('instances')

    def __unicode__(self):
        return self.name

    @classmethod
    def create_from_template(cls, template, owner, **kwargs):
        """Create a new instance based on an InstanceTemplate.

        Can also specify parameters as keyword arguments which should override
        template settings.
        """
        # prepare parameters
        kwargs['template'] = template
        kwargs['owner'] = owner
        kwargs.setdefault('name', template.name)
        kwargs.setdefault('description', template.description)
        kwargs.setdefault('pw', pwgen())
        kwargs.setdefault('num_cores', template.num_cores)
        kwargs.setdefault('ram_size', template.ram_size)
        kwargs.setdefault('max_ram_size', template.max_ram_size)
        kwargs.setdefault('arch', template.arch)
        kwargs.setdefault('priority', template.priority)
        kwargs.setdefault('boot_menu', template.boot_menu)
        kwargs.setdefault('raw_data', template.raw_data)
        kwargs.setdefault('lease', template.lease)
        kwargs.setdefault('access_method', template.access_method)
        # create instance and do additional setup
        inst = cls(**kwargs)
        for disk in template.disks:
            inst.disks.add(disk.get_exclusive())
        # save instance
        inst.save()
        # create related entities
        for iftmpl in template.interface_set.all():
            i = Interface.create_from_template(instance=inst, template=iftmpl)
            if i.host:
                i.host.enable_net()
                port, proto = ACCESS_PROTOCOLS[i.access_method][1:3]
                i.host.add_port(proto, i.get_port(), port)

        return inst

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
        return self.primary_host.ipv4 if self.primary_host else None

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
    def uptime(self):
        """Uptime of the instance.
        """
        if self.active_since:
            return timezone.now() - self.active_since
        else:
            return timedelta()  # zero

    def get_age(self):
        """Deprecated. Use uptime instead.

        Get age of VM in seconds.
        """
        return self.uptime.seconds

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
        if not self.firewall_host:
            return _('None')
        proto = 'ipv6' if use_ipv6 else 'ipv4'
        return self.firewall_host.get_hostname(proto=proto)

    def get_connect_uri(self, use_ipv6=False):
        """Get access parameters in URI format.
        """
        try:
            port = self.get_connect_port(use_ipv6=use_ipv6)
            host = self.get_connect_host(use_ipv6=use_ipv6)
            proto = self.access_method
            if proto == 'ssh':
                proto = 'sshterm'
            return ('%(proto)s:cloud:%(pw)s:%(host)s:%(port)d' %
                    {'port': port, 'proto': proto, 'pw': self.pw,
                     'host': host})
        except:
            return

    def get_vm_desc(self):
        return {
            'name': self.vm_name,
            'vcpu': self.num_cores,
            'memory': self.ram_size,
            'memory_max': self.max_ram_size,
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
            'raw_data': "" if not self.raw_data else self.raw_data
        }

    def deploy_async(self, user=None):
        """ Launch celery task to handle the job asynchronously.
        """
        vm_manager.deploy.apply_async(args=[self, user], queue="localhost.man")

    def deploy(self, user=None, task_uuid=None):
        """ Deploy new virtual machine with network
        1. Schedule
        """
        act = InstanceActivity(activity_code='vm.Instance.deploy')
        act.instance = self
        act.user = user
        act.started = timezone.now()
        act.task_uuid = task_uuid
        act.save()

        # Schedule
        act.update_state("PENDING")
        self.node = scheduler.get_node(self, Node.objects.all())
        self.save()

        # Create virtual images
        act.update_state("PREPARING DISKS")
        for disk in self.disks.all():
            disk.deploy()

        # Deploy VM on remote machine
        act.update_state("DEPLOYING VM")
        tasks.create.apply_async(args=[self.get_vm_desc()],
                                 queue=self.node.host.hostname + ".vm").get()

        # Estabilish network connection (vmdriver)
        act.update_state("DEPLOYING NET")
        for net in self.interface_set.all():
            net.deploy()

        # Resume vm
        act.update_state("BOOTING")
        tasks.resume.apply_async(args=[self.vm_name],
                                 queue=self.node + ".vm").get()

        act.finish(result='SUCCESS')

    def stop_async(self, user=None):
        vm_manager.stop.apply_async(args=[self, user], queue="localhost.man")

    def stop(self, user=None, task_uuid=None):
        act = InstanceActivity(activity_code='vm.Instance.stop')
        act.instance = self
        act.user = user
        act.started = timezone.now()
        act.task_uuid = task_uuid
        act.save()
        tasks.stop.apply_async(args=[self.get_vm_desc()],
                               queue=self.node.host.hostname + ".vm").get()

    def resume_async(self, user=None):
        vm_manager.resume.apply_async(args=[self, user], queue="localhost.man")

    def resume(self, user=None, task_uuid=None):
        act = InstanceActivity(activity_code='vm.Instance.resume')
        act.instance = self
        act.user = user
        act.started = timezone.now()
        act.task_uuid = task_uuid
        act.save()
        tasks.resume.apply_async(args=[self.get_vm_desc()],
                                 queue=self.node.host.hostname + ".vm").get()

    def poweroff_async(self, user=None):
        vm_manager.power_off.apply_async(args=[self, user],
                                         queue="localhost.man")

    def poweroff(self, user=None, task_uuid=None):
        act = InstanceActivity(activity_code='vm.Instance.power_off')
        act.instance = self
        act.user = user
        act.started = timezone.now()
        act.task_uuid = task_uuid
        act.save()
        tasks.power_off.apply_async(args=[self.get_vm_desc()],
                                    queue=self.node.host.hostname + ".vm"
                                    ).get()

    def restart_async(self, user=None):
        vm_manager.restart.apply_async(args=[self, user],
                                       queue="localhost.man")

    def restart(self, user=None, task_uuid=None):
        act = InstanceActivity(activity_code='vm.Instance.restart')
        act.instance = self
        act.user = user
        act.started = timezone.now()
        act.task_uuid = task_uuid
        act.save()
        tasks.restart.apply_async(args=[self.get_vm_desc()],
                                  queue=self.node.host.hostname + ".vm").get()

    def save_as_async(self, user=None):
        vm_manager.save_as.apply_async(
            args=[self, user], queue="localhost.man")

    def save_as(self, user=None, task_uuid=None):
        act = InstanceActivity(activity_code='vm.Instance.restart')
        act.instance = self
        act.user = user
        act.started = timezone.now()
        act.task_uuid = task_uuid
        act.save()
        tasks.save_as.apply_async(args=[self.get_vm_desc()],
                                  queue=self.node.host.hostname + ".vm").get()

    def renew(self, which='both'):
        """Renew virtual machine instance leases.
        """
        if which not in ['suspend', 'delete', 'both']:
            raise ValueError('No such expiration type.')
        if which in ['suspend', 'both']:
            self.time_of_suspend = timezone.now() + self.lease.suspend_interval
        if which in ['delete', 'both']:
            self.time_of_delete = timezone.now() + self.lease.delete_interval
        self.save()


@receiver(pre_delete, sender=Instance, dispatch_uid='delete_instance_pre')
def delete_instance_pre(sender, instance, using, **kwargs):
    # TODO implement
    pass


class InstanceActivity(TimeStampedModel):
    activity_code = CharField(verbose_name=_('activity_code'), max_length=100)
    task_uuid = CharField(verbose_name=_('task_uuid'), blank=True,
                          max_length=50, null=True, unique=True)
    instance = ForeignKey(Instance, verbose_name=_('instance'),
                          related_name='activity_log')
    user = ForeignKey(User, verbose_name=_('user'), blank=True, null=True)
    started = DateTimeField(verbose_name=_('started'), blank=True, null=True)
    finished = DateTimeField(verbose_name=_('finished'), blank=True, null=True)
    result = TextField(verbose_name=_('result'), blank=True, null=True)
    state = CharField(verbose_name=_('state'),
                      default='PENDING', max_length=50)

    def update_state(self, new_state):
        self.state = new_state
        self.save()

    def finish(self, result=None):
        if not self.finished:
            self.finished = timezone.now()
            self.result = result
            self.save()


class Interface(Model):

    """Network interface for an instance.
    """
    vlan = ForeignKey(Vlan, verbose_name=_('vlan'),
                      related_name="vm_interface")
    host = ForeignKey(Host, verbose_name=_('host'),  blank=True, null=True)
    instance = ForeignKey(Instance, verbose_name=_('instance'),
                          related_name='interface_set')

    @property
    def mac(self):
        try:
            return self.host.mac
        except:
            return Interface.generate_mac(self.instance, self.vlan)

    @classmethod
    def generate_mac(cls, instance, vlan):
        """Generate MAC address for a VM instance on a VLAN.
        """
        # MAC 02:XX:XX:XX:XX:XX
        #        \________/\__/
        #           VM ID   VLAN ID
        i = instance.id & 0xfffffff
        v = vlan.vid & 0xfff
        m = (0x02 << 40) | (i << 12) | v
        return EUI(m)

    def get_vmnetwork_desc(self):
        return {
            'name': 'cloud-' + self.instance.id + '-' + self.vlan.vid,
            'bridge': 'cloud',
            'mac': self.mac,
            'ipv4': self.host.ipv4 if self.host is not None else None,
            'ipv6': self.host.ipv6 if self.host is not None else None,
            'vlan': self.vlan.vid,
            'managed': self.host is not None
        }

    @classmethod
    def create_from_template(cls, instance, template):
        """Create a new interface for an instance based on an
           InterfaceTemplate.
        """
        host = (Host(vlan=template.vlan, mac=cls.generate_mac(instance,
                                                              template.vlan))
                if template.managed else None)
        iface = cls(vlan=template.vlan, host=host, instance=instance)
        iface.save()
        return iface
