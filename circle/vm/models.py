from contextlib import contextmanager
from datetime import timedelta
from importlib import import_module
import logging
from netaddr import EUI, mac_unix

import django.conf
from django.contrib.auth.models import User
from django.core import signing
from django.db.models import (Model, ForeignKey, ManyToManyField, IntegerField,
                              DateTimeField, BooleanField, TextField,
                              CharField, permalink)
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from model_utils.models import TimeStampedModel
from taggit.managers import TaggableManager

from .tasks import local_tasks, vm_tasks, net_tasks
from firewall.models import Vlan, Host
from storage.models import Disk
from common.models import ActivityModel, activitycontextimpl
from django.core import signing


logger = logging.getLogger(__name__)
pwgen = User.objects.make_random_password
scheduler = import_module(name=django.conf.settings.VM_SCHEDULER)
ACCESS_PROTOCOLS = django.conf.settings.VM_ACCESS_PROTOCOLS
ACCESS_METHODS = [(key, name) for key, (name, port, transport)
                  in ACCESS_PROTOCOLS.iteritems()]
ARCHITECTURES = (('x86_64', 'x86-64 (64 bit)'),
                 ('i686', 'x86 (32 bit)'))
VNC_PORT_RANGE = (2000, 65536)  # inclusive start, exclusive end


class BaseResourceConfigModel(Model):

    """Abstract base for models with base resource configuration parameters.
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


class VirtualMachineDescModel(BaseResourceConfigModel):
    """Abstract base for virtual machine describing models.
    """
    access_method = CharField(max_length=10, choices=ACCESS_METHODS,
                              verbose_name=_('access method'),
                              help_text=_('Primary remote access method.'))
    boot_menu = BooleanField(verbose_name=_('boot menu'), default=False,
                             help_text=_(
                                 'Show boot device selection menu on boot.'))
    raw_data = TextField(verbose_name=_('raw_data'), blank=True, help_text=_(
        'Additional libvirt domain parameters in XML format.'))
    tags = TaggableManager()

    class Meta:
        abstract = True


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
    tags = TaggableManager()

    class Meta:
        permissions = ()

    @property
    def online(self):
        """Indicates whether the node is connected and functional.
        """
        pass  # TODO implement check

    def __unicode__(self):
        return self.name


class NodeActivity(ActivityModel):
    node = ForeignKey(Node, related_name='activity_log',
                      help_text=_('Node this activity works on.'),
                      verbose_name=_('node'))

    @classmethod
    def create(cls, code_suffix, node, task_uuid=None, user=None):
        act = cls(activity_code='vm.Node.' + code_suffix,
                  node=node, parent=None, started=timezone.now(),
                  task_uuid=task_uuid, user=user)
        act.save()
        return act

    def create_sub(self, code_suffix, task_uuid=None):
        act = NodeActivity(
            activity_code=self.activity_code + '.' + code_suffix,
            node=self.node, parent=self, started=timezone.now(),
            task_uuid=task_uuid, user=self.user)
        act.save()
        return act

    @contextmanager
    def sub_activity(self, code_suffix, task_uuid=None):
        act = self.create_sub(code_suffix, task_uuid)
        return activitycontextimpl(act)


@contextmanager
def node_activity(code_suffix, node, task_uuid=None, user=None):
    act = InstanceActivity.create(code_suffix, node, task_uuid, user)
    return activitycontextimpl(act)


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


class InstanceTemplate(VirtualMachineDescModel, TimeStampedModel):

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
                          help_text=_('Template the interface '
                                      'template belongs to.'))

    class Meta:
        permissions = ()
        verbose_name = _('interface template')
        verbose_name_plural = _('interface templates')


class Instance(VirtualMachineDescModel, TimeStampedModel):

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
                     help_text=_("Human readable name of instance."))
    description = TextField(blank=True, verbose_name=_('description'))
    template = ForeignKey(InstanceTemplate, blank=True, null=True,
                          related_name='instance_set',
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
    active_since = DateTimeField(blank=True, null=True,
                                 help_text=_("Time stamp of successful "
                                             "boot report."),
                                 verbose_name=_('active since'))
    node = ForeignKey(Node, blank=True, null=True,
                      related_name='instance_set',
                      help_text=_("Current hypervisor of this instance."),
                      verbose_name=_('host node'))
    state = CharField(choices=STATES, default='NOSTATE', max_length=20)
    disks = ManyToManyField(Disk, related_name='instance_set',
                            help_text=_("Set of mounted disks."),
                            verbose_name=_('disks'))
    lease = ForeignKey(Lease, help_text=_("Preferred expiration periods."))
    vnc_port = IntegerField(blank=True, default=None, null=True,
                            help_text=_("TCP port where VNC console listens."),
                            unique=True, verbose_name=_('vnc_port'))
    owner = ForeignKey(User)
    destoryed = DateTimeField(blank=True, null=True,
                              help_text=_("The virtual machine's time of "
                                          "destruction."))

    class Meta:
        ordering = ['pk', ]
        permissions = ()
        verbose_name = _('instance')
        verbose_name_plural = _('instances')

    def __unicode__(self):
        parts = [self.name, "(" + str(self.id) + ")"]
        return " ".join([s for s in parts if s != ""])

    @classmethod
    def create_from_template(cls, template, owner, disks=None, networks=None,
                             **kwargs):
        """Create a new instance based on an InstanceTemplate.

        Can also specify parameters as keyword arguments which should override
        template settings.
        """
        disks = template.disks.all() if disks is None else disks

        networks = (template.interface_set.all() if networks is None
                    else networks)

        # prepare parameters
        kwargs['template'] = template
        kwargs['owner'] = owner
        kwargs.setdefault('pw', pwgen())
        ca = ['name', 'description', 'num_cores', 'ram_size', 'max_ram_size',
              'arch', 'priority', 'boot_menu', 'raw_data', 'lease',
              'access_method']
        for attr in ca:
            kwargs.setdefault(attr, getattr(template, attr))
        # create instance and do additional setup
        inst = cls(**kwargs)
        # save instance
        inst.clean()
        inst.save()
        # create related entities
        for disk in disks:
            inst.disks.add(disk.get_exclusive())

        for net in networks:
            i = Interface.create(instance=inst, vlan=net.vlan, owner=owner,
                                 managed=net.managed)

            if i.host:
                i.host.enable_net()
                port, proto = ACCESS_PROTOCOLS[i.instance.access_method][1:3]
                # TODO fix this port fw
                i.host.add_port(proto, private=port)

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
    def mem_dump(self):
        """Return the path for the memory dump.

        It is always on the first hard drive storage named cloud-<id>.dump
        """
        path = self.disks.all()[0].datastore.path
        return path + '/' + self.vm_name + '.dump'

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
            'memory': int(self.ram_size) * 1024,  # convert from MiB to KiB
            'memory_max': int(self.max_ram_size) * 1024,  # convert from MiB to KiB
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

    def get_remote_queue_name(self, queue_id):
        """Get the remote worker queue name of this instance with the specified
           queue ID.
        """
        return self.node.host.hostname + "." + queue_id

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

    def deploy(self, user=None, task_uuid=None):
        """Deploy new virtual machine with network

        :param self: The virtual machine to deploy.
        :type self: vm.models.Instance

        :param user: The user who's issuing the command.
        :type user: django.contrib.auth.models.User

        :param task_uuid: The task's UUID, if the command is being executed
                          asynchronously.
        :type task_uuid: str
        """
        with instance_activity(code_suffix='deploy', instance=self,
                               task_uuid=task_uuid, user=user) as act:

            # Find unused port for VNC
            if self.vnc_port is None:
                used = Instance.objects.values_list('vnc_port', flat=True)
                for p in xrange(*VNC_PORT_RANGE):
                    if p not in used:
                        self.vnc_port = p
                        break
                else:
                    raise Exception("No unused port could be found for VNC.")

            # Schedule
            self.node = scheduler.get_node(self, Node.objects.all())
            self.save()

            # Deploy virtual images
            with act.sub_activity('deploying_disks'):
                for disk in self.disks.all():
                    disk.deploy()

            queue_name = self.get_remote_queue_name('vm')
            # Deploy VM on remote machine
            with act.sub_activity('deploying_vm'):
                vm_tasks.deploy.apply_async(args=[self.get_vm_desc()],
                                            queue=queue_name).get()

            # Estabilish network connection (vmdriver)
            with act.sub_activity('deploying_net'):
                for net in self.interface_set.all():
                    net.deploy()

            # Resume vm
            with act.sub_activity('booting'):
                vm_tasks.resume.apply_async(args=[self.vm_name],
                                            queue=queue_name).get()

    def deploy_async(self, user=None):
        """Execute deploy asynchronously.
        """
        return local_tasks.deploy.apply_async(args=[self, user],
                                              queue="localhost.man")

    def destroy(self, user=None, task_uuid=None):
        """Remove virtual machine and its networks.

        :param self: The virtual machine to destroy.
        :type self: vm.models.Instance

        :param user: The user who's issuing the command.
        :type user: django.contrib.auth.models.User

        :param task_uuid: The task's UUID, if the command is being executed
                          asynchronously.
        :type task_uuid: str
        """
        with instance_activity(code_suffix='destroy', instance=self,
                               task_uuid=task_uuid, user=user) as act:

            # Destroy networks
            with act.sub_activity('destroying_net'):
                for net in self.interface_set.all():
                    net.destroy()

            # Destroy virtual machine
            with act.sub_activity('destroying_vm'):
                queue_name = self.get_remote_queue_name('vm')
                vm_tasks.destroy.apply_async(args=[self.vm_name],
                                             queue=queue_name).get()

            # Destroy disks
            with act.sub_activity('destroying_disks'):
                for disk in self.disks.all():
                    disk.destroy()

            # Clear node and VNC port association
            self.node = None
            self.vnc_port = None

            self.destoryed = timezone.now()
            self.save()

    def destroy_async(self, user=None):
        """Execute destroy asynchronously.
        """
        return local_tasks.destroy.apply_async(args=[self, user],
                                               queue="localhost.man")

    def sleep(self, user=None, task_uuid=None):
        """Suspend virtual machine with memory dump.
        """
        with instance_activity(code_suffix='sleep', instance=self,
                               task_uuid=task_uuid, user=user):

            queue_name = self.get_remote_queue_name('vm')
            vm_tasks.sleep.apply_async(args=[self.vm_name, self.mem_dump],
                                       queue=queue_name).get()

    def sleep_async(self, user=None):
        """Execute sleep asynchronously.
        """
        return local_tasks.sleep.apply_async(args=[self, user],
                                             queue="localhost.man")

    def wake_up(self, user=None, task_uuid=None):
        with instance_activity(code_suffix='wake_up', instance=self,
                               task_uuid=task_uuid, user=user):

            queue_name = self.get_remote_queue_name('vm')
            vm_tasks.resume.apply_async(args=[self.vm_name, self.dump_mem],
                                        queue=queue_name).get()

    def wake_up_async(self, user=None):
        """Execute wake_up asynchronously.
        """
        return local_tasks.wake_up.apply_async(args=[self, user],
                                               queue="localhost.man")

    def shutdown(self, user=None, task_uuid=None):
        """Shutdown virtual machine with ACPI signal.
        """
        with instance_activity(code_suffix='shutdown', instance=self,
                               task_uuid=task_uuid, user=user):

            queue_name = self.get_remote_queue_name('vm')
            vm_tasks.shutdown.apply_async(args=[self.vm_name],
                                          queue=queue_name).get()

    def shutdown_async(self, user=None):
        """Execute shutdown asynchronously.
        """
        return local_tasks.shutdown.apply_async(args=[self, user],
                                                queue="localhost.man")

    def reset(self, user=None, task_uuid=None):
        """Reset virtual machine (reset button)
        """
        with instance_activity(code_suffix='reset', instance=self,
                               task_uuid=task_uuid, user=user):

            queue_name = self.get_remote_queue_name('vm')
            vm_tasks.restart.apply_async(args=[self.vm_name],
                                         queue=queue_name).get()

    def reset_async(self, user=None):
        """Execute reset asynchronously.
        """
        return local_tasks.restart.apply_async(args=[self, user],
                                               queue="localhost.man")

    def reboot(self, user=None, task_uuid=None):
        """Reboot virtual machine with Ctrl+Alt+Del signal.
        """
        with instance_activity(code_suffix='reboot', instance=self,
                               task_uuid=task_uuid, user=user):

            queue_name = self.get_remote_queue_name('vm')
            vm_tasks.reboot.apply_async(args=[self.vm_name],
                                        queue=queue_name).get()

    def reboot_async(self, user=None):
        """Execute reboot asynchronously.
        """
        return local_tasks.reboot.apply_async(args=[self, user],
                                              queue="localhost.man")

    def save_as_template(self, name, **kwargs):
        # prepare parameters
        kwargs.setdefault('name', name)
        kwargs.setdefault('description', self.description)
        kwargs.setdefault('parent', self.template)
        kwargs.setdefault('num_cores', self.num_cores)
        kwargs.setdefault('ram_size', self.ram_size)
        kwargs.setdefault('max_ram_size', self.max_ram_size)
        kwargs.setdefault('arch', self.arch)
        kwargs.setdefault('priority', self.priority)
        kwargs.setdefault('boot_menu', self.boot_menu)
        kwargs.setdefault('raw_data', self.raw_data)
        kwargs.setdefault('lease', self.lease)
        kwargs.setdefault('access_method', self.access_method)
        kwargs.setdefault('system', self.template.system
                          if self.template else None)
        # create template and do additional setup
        tmpl = InstanceTemplate(**kwargs)
        # save template
        tmpl.save()
        # create related entities
        for disk in self.disks.all():
            try:
                d = disk.save_as()
            except Disk.WrongDiskTypeError:
                d = disk

            tmpl.disks.add(d)

        for i in self.interface_set.all():
            i.save_as_template(tmpl)

        return tmpl


class InstanceActivity(ActivityModel):
    instance = ForeignKey(Instance, related_name='activity_log',
                          help_text=_('Instance this activity works on.'),
                          verbose_name=_('instance'))

    def __unicode__(self):
        if self.parent:
            return self.parent.activity_code + "(" + self.instance.name + ")" + "->" + self.activity_code
        else:
            return self.activity_code + "(" + self.instance.name + ")"

    @classmethod
    def create(cls, code_suffix, instance, task_uuid=None, user=None):
        act = cls(activity_code='vm.Instance.' + code_suffix,
                  instance=instance, parent=None, started=timezone.now(),
                  task_uuid=task_uuid, user=user)
        act.save()
        return act

    def create_sub(self, code_suffix, task_uuid=None):
        act = InstanceActivity(
            activity_code=self.activity_code + '.' + code_suffix,
            instance=self.instance, parent=self, started=timezone.now(),
            task_uuid=task_uuid, user=self.user)
        act.save()
        return act

    @contextmanager
    def sub_activity(self, code_suffix, task_uuid=None):
        act = self.create_sub(code_suffix, task_uuid)
        return activitycontextimpl(act)


@contextmanager
def instance_activity(code_suffix, instance, task_uuid=None, user=None):
    act = InstanceActivity.create(code_suffix, instance, task_uuid, user)
    return activitycontextimpl(act)


class Interface(Model):

    """Network interface for an instance.
    """
    vlan = ForeignKey(Vlan, verbose_name=_('vlan'),
                      related_name="vm_interface")
    host = ForeignKey(Host, verbose_name=_('host'),  blank=True, null=True)
    instance = ForeignKey(Instance, verbose_name=_('instance'),
                          related_name='interface_set')

    def __unicode__(self):
        return 'cloud-' + str(self.instance.id) + '-' + str(self.vlan.vid)

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
        return EUI(m, dialect=mac_unix)

    def get_vmnetwork_desc(self):
        return {
            'name': self.__unicode__(),
            'bridge': 'cloud',
            'mac': str(self.mac),
            'ipv4': str(self.host.ipv4) if self.host is not None else None,
            'ipv6': str(self.host.ipv6) if self.host is not None else None,
            'vlan': self.vlan.vid,
            'managed': self.host is not None
        }

    def deploy(self, user=None, task_uuid=None):
        net_tasks.create.apply_async(
            args=[self.get_vmnetwork_desc()],
            queue=self.instance.get_remote_queue_name('net'))

    def destroy(self, user=None, task_uuid=None):
        net_tasks.destroy.apply_async(
            args=[self.get_vmnetwork_desc()],
            queue=self.instance.get_remote_queue_name('net'))

    @classmethod
    def create(cls, instance, vlan, managed, owner=None):
        """Create a new interface for a VM instance to the specified VLAN.
        """
        if managed:
            host = Host()
            host.vlan = vlan
            # TODO change Host's mac field's type to EUI in firewall
            host.mac = str(cls.generate_mac(instance, vlan))
            host.hostname = instance.vm_name
            # Get adresses from firewall
            addresses = vlan.get_new_address()
            host.ipv4 = addresses['ipv4']
            host.ipv6 = addresses['ipv6']
            host.owner = owner
            host.save()
        else:
            host = None

        iface = cls(vlan=vlan, host=host, instance=instance)
        iface.save()
        return iface

    def save_as_template(self, instance_template):
        """Create a template based on this interface.
        """
        i = InterfaceTemplate(vlan=self.vlan, managed=self.host is not None,
                              template=instance_template)
        i.save()
        return i
