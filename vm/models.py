from datetime import timedelta
import logging

from django.conf.settings import CLOUD_URL
from django.contrib.auth.models import User
# from django.core import signing
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.template.defaultfilters import escape
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from model_utils.models import TimeStampedModel

from firewall.models import Vlan, Host
from storage.models import Disk

logger = logging.getLogger(__name__)
pwgen = User.objects.make_random_password
# TODO get this from config
ACCESS_PROTOCOLS = {
    # format: id: (name, port, protocol)
    'rdp': ('rdp', 3389, 'tcp'),
    'nx': ('nx', 22, 'tcp'),
    'ssh': ('ssh', 22, 'tcp'),
}
ACCESS_METHODS = [(k, ap[0]) for k, ap in ACCESS_PROTOCOLS.iteritems()]


class BaseResourceConfigModel(models.Model):
    """Abstract base class for models with base resource configuration
       parameters.
    """
    num_cores = models.IntegerField(help_text=_('Number of CPU cores.'))
    ram_size = models.IntegerField(help_text=_('Mebibytes of memory.'))
    max_ram_size = models.IntegerField(help_text=_('Upper memory size limit '
                                                   'for balloning.'))
    arch = models.CharField(max_length=10, verbose_name=_('architecture'))
    priority = models.IntegerField(help_text=_('instance priority'))

    class Meta:
        abstract = True


class NamedBaseResourceConfig(BaseResourceConfigModel, TimeStampedModel):
    """Pre-created, named base resource configurations.
    """
    name = models.CharField(max_length=50, unique=True,
                            verbose_name=_('name'))

    def __unicode__(self):
        return self.name


class Node(TimeStampedModel):
    name = models.CharField(max_length=50, unique=True,
                            verbose_name=_('name'))
    num_cores = models.IntegerField(help_text=_('Number of CPU cores.'))
    ram_size = models.IntegerField(help_text=_('Mebibytes of memory.'))
    priority = models.IntegerField(help_text=_('node usage priority'))
    host = models.ForeignKey(Host)
    enabled = models.BooleanField(default=False,
                                  help_text=_('Indicates whether the node can '
                                              'be used for hosting.'))

    class Meta:
        permissions = ()

    @property
    def online(self):
        """Indicates whether the node is connected and functional.
        """
        pass  # TODO implement check


class Lease(models.Model):
    """Lease times for VM instances.

    Specifies a time duration until suspension and deletion of a VM
    instance.
    """
    name = models.CharField(max_length=100, unique=True,
                            verbose_name=_('name'))
    suspend_interval_seconds = models.IntegerField()
    delete_interval_seconds = models.IntegerField()

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
      * ownership information
    """
    STATES = [('NEW', _('new')),  # template has just been created
              ('SAVING', _('saving')),  # changes are being saved
              ('READY', _('ready'))]  # template is ready for instantiation
    name = models.CharField(max_length=100, unique=True,
                            verbose_name=_('name'))
    description = models.TextField(verbose_name=_('description'),
                                   blank=True)
    parent = models.ForeignKey('self', null=True, blank=True,
                               verbose_name=_('parent template'))
    system = models.TextField(verbose_name=_('operating system'),
                              blank=True,
                              help_text=(_('Name of operating system in '
                                           'format like "%s".') %
                                         'Ubuntu 12.04 LTS Desktop amd64'))
    access_method = models.CharField(max_length=10, choices=ACCESS_METHODS,
                                     verbose_name=_('access method'))
    state = models.CharField(max_length=10, choices=STATES,
                             default='NEW')
    disks = models.ManyToManyField(Disk, verbose_name=_('disks'),
                                   related_name='template_set')
    lease = models.ForeignKey(Lease, related_name='template_set')

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
            return "win"
        else:
            return "linux"


class InterfaceTemplate(models.Model):
    """Network interface template for an instance template.

    If the interface is managed, a host will be created for it.
    """
    vlan = models.ForeignKey(Vlan)
    managed = models.BooleanField(default=True)
    template = models.ForeignKey(InstanceTemplate,
                                 related_name='interface_set')

    class Meta:
        permissions = ()
        verbose_name = _('interface template')
        verbose_name_plural = _('interface templates')


def create_context(pw, hostname, smb_password, ssh_private_key, owner, token,
                   extra):
    """Return XML context configuration with given parameters.
    """
    return u'''
            <SOURCE>web</SOURCE>
            <HOSTNAME>%(hostname)s</HOSTNAME>
            <NEPTUN>%(neptun)s</NEPTUN>
            <USERPW>%(pw)s</USERPW>
            <SMBPW>%(smbpw)s</SMBPW>
            <SSHPRIV>%(sshkey)s</SSHPRIV>
            <BOOTURL>%(booturl)s</BOOTURL>
            <SERVER>store.cloud.ik.bme.hu</SERVER>
            %(extra)s
    ''' % {
        "pw": escape(pw),
        "hostname": escape(hostname),
        "smbpw": escape(smb_password),
        "sshkey": escape(ssh_private_key),
        "neptun": escape(owner),
        "booturl": "%sb/%s/" % (CLOUD_URL, token),
        "extra": extra
    }


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
      * current state (libvirt domain state) and operation (Celery job UUID)
      * time of creation and last modification
      * base resource configuration values
      * ownership information
    """
    STATES = [('NOSTATE', _('nostate')),
              ('RUNNING', _('running')),
              ('BLOCKED', _('blocked')),
              ('PAUSED', _('paused')),
              ('SHUTDOWN', _('shutdown')),
              ('SHUTOFF', _('shutoff')),
              ('CRASHED', _('crashed')),
              ('PMSUSPENDED', _('pmsuspended'))]  # libvirt domain states
    name = models.CharField(blank=True, max_length=100, verbose_name=_('name'))
    description = models.TextField(blank=True, verbose_name=_('description'))
    template = models.ForeignKey(InstanceTemplate, blank=True, null=True,
                                 related_name='instance_set',
                                 verbose_name=_('template'))
    pw = models.CharField(help_text=_('Original password of instance'),
                          max_length=20, verbose_name=_('password'))
    time_of_suspend = models.DateTimeField(blank=True, default=None, null=True,
                                           verbose_name=_('time of suspend'))
    time_of_delete = models.DateTimeField(blank=True, default=None, null=True,
                                          verbose_name=_('time of delete'))
    active_since = models.DateTimeField(blank=True, null=True,
                                        help_text=_('Time stamp of successful '
                                                    'boot report.'),
                                        verbose_name=_('active since'))
    node = models.ForeignKey(Node, blank=True, null=True,
                             related_name='instance_set',
                             verbose_name=_('host nose'))
    state = models.CharField(choices=STATES, default='NOSTATE', max_length=20)
    operation = models.CharField(blank=True, max_length=100, null=True,
                                 verbose_name=_('operation'))
    disks = models.ManyToManyField(Disk, related_name='instance_set',
                                   verbose_name=_('disks'))
    lease = models.ForeignKey(Lease)
    access_method = models.CharField(max_length=10, choices=ACCESS_METHODS,
                                     verbose_name=_('access method'))
    owner = models.ForeignKey(User)

    class Meta:
        ordering = ['pk', ]
        permissions = ()
        verbose_name = _('instance')
        verbose_name_plural = _('instances')

    def __unicode__(self):
        return self.name

    @classmethod
    def create_from_template(cls, template, **kwargs):
        """Create a new instance based on an InstanceTemplate.

        Can also specify parameters as keyword arguments which should override
        template settings.
        """
        # prepare parameters
        kwargs['template'] = template
        kwargs.setdefault('name', template.name)
        kwargs.setdefault('description', template.description)
        kwargs.setdefault('pw', pwgen())
        kwargs.setdefault('num_cores', template.num_cores)
        kwargs.setdefault('ram_size', template.ram_size)
        kwargs.setdefault('max_ram_size', template.max_ram_size)
        kwargs.setdefault('arch', template.arch)
        kwargs.setdefault('priority', template.priority)
        kwargs.setdefault('lease', template.lease)
        kwargs.setdefault('access_method', template.access_method)
        # create instance and do additional setup
        inst = cls(**kwargs)
        for disk in template.disks:
            inst.disks.add(disk.get_exculsive())
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

    # TODO is this obsolete?
    @models.permalink
    def get_absolute_url(self):
        return ('one.views.vm_show', None, {'iid': self.id})

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
        """Primary IPv4 address of the instance."""
        return self.primary_host.ipv4 if self.primary_host else None

    @property
    def ipv6(self):
        """Primary IPv6 address of the instance."""
        return self.primary_host.ipv6 if self.primary_host else None

    @property
    def mac(self):
        """Primary MAC address of the instance."""
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
        return self.operation is not None

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
            return ("%(proto)s:cloud:%(pw)s:%(host)s:%(port)d" %
                    {"port": port, "proto": proto, "pw": self.pw,
                     "host": host})
        except:
            return

    def deploy(self, extra=""):
        # TODO implement
        pass
        #    """Submit a new instance to OpenNebula."""
        #    inst = Instance(pw=pwgen(), template=template, owner=owner,
        #                    share=share, state='PENDING', waiting=True)
        #    inst.save()
        #    hostname = u"%d" % (inst.id, )
        #    token = signing.dumps(inst.id, salt='activate')
        #    try:
        #        details = owner.cloud_details
        #    except:
        #        details = UserCloudDetails(user=owner)
        #        details.save()
        #
        #    ctx = create_context(inst.pw, hostname, details.smb_password,
        #                              details.ssh_private_key, owner.username,
        #                              token, extra)
        #    try:
        #        from .tasks import CreateInstanceTask
        #        x = CreateInstanceTask.delay(
        #            name=u"%s %d" % (owner.username, inst.id),
        #            instance_type=template.instance_type.name,
        #            disk_id=int(template.disk.id),
        #            network_id=int(template.network.id),
        #            ctx=ctx,
        #        )
        #        res = x.get(timeout=10)
        #        res['one_id']
        #    except:
        #        inst.delete()
        #        raise Exception("Unable to create VM instance.")
        #
        #    inst.one_id = res['one_id']
        #    inst.ip = res['interfaces'][0]['ip']
        #    inst.name = ("%(neptun)s %(template)s (%(id)d)" %
        #                 {'neptun': owner.username, 'template': template.name,
        #                  'id': inst.one_id})
        #    inst.save()
        #
        #    inst._create_host(hostname, res)
        #    return inst

    def stop(self):
        # TODO implement
        pass

    def resume(self):
        # TODO implement
        pass

    def poweroff(self):
        # TODO implement
        pass

    def restart(self):
        # TODO implement
        pass

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

    def save_as(self):
        """Save image and shut down."""
        imgname = "template-%d-%d" % (self.template.id, self.id)
        from .tasks import SaveAsTask
        SaveAsTask.delay(one_id=self.one_id, new_img=imgname)
        self._change_state("SHUTDOWN")
        self.save()
        t = self.template
        t.state = 'SAVING'
        t.save()

    def check_if_is_save_as_done(self):
        if self.state != 'DONE':
            return False
        Disk.update(delete=False)
        imgname = "template-%d-%d" % (self.template.id, self.id)
        disks = Disk.objects.filter(name=imgname)
        if len(disks) != 1:
            return False
        self.template.disk_id = disks[0].id
        self.template.state = 'READY'
        self.template.save()
        self.firewall_host_delete()
        return True


@receiver(pre_delete, sender=Instance, dispatch_uid="delete_instance_pre")
def delete_instance_pre(sender, instance, using, **kwargs):
    # TODO implement
    pass


class Interface(models.Model):
    """Network interface for an instance.
    """
    vlan = models.ForeignKey(Vlan)
    host = models.ForeignKey(Host, blank=True, null=True)
    instance = models.ForeignKey(Instance, related_name='interface_set')

    @classmethod
    def create_from_template(cls, instance, template):
        """Create a new interface for an instance based on an
           InterfaceTemplate.
        """
        host = Host(vlan=template.vlan) if template.managed else None
        iface = cls(vlan=template.vlan, host=host, instance=instance)
        iface.save()
        return iface
