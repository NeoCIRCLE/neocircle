from django.db import models
from model_utils.models import TimeStampedModel
from firewall.models import Vlan
from storage.models import Disk, Image


class BaseResourceConfigModel():
    """Abstract base class for models with base resource configuration
       parameters.
    """
    CPU = models.IntegerField(help_text=_('CPU cores.'))
    RAM = models.IntegerField(help_text=_('Mebibytes of memory.'))
    max_RAM = models.IntegerField(help_text=_('Upper memory size limit for '
                                              'balloning.'))
    arch = models.CharField(max_length=10, verbose_name=_('architecture'))
    priority = models.IntegerField(help_text=_('instance priority'))

    class Meta:
        abstract = True


class NamedBaseResourceConfig(models.Model, BaseResourceConfigModel):
    """Pre-created, named base resource configurations.
    """
    name = models.CharField(max_length=50, unique=True,
                            verbose_name=_('name'))

    def __unicode__(self):
        return self.name


class Interface(models.Model):
    """Network interface for an instance.
    """
    vlan = models.ForeignKey(Vlan)
    host = models.ForeignKey(Host)
    instance = models.ForeignKey(Instance)


class InterfaceTemplate(models.Model):
    """Network interface template for an instance template.
    """
    vlan = models.ForeignKey(Vlan)
    managed = models.BooleanField()
    template = models.ForeignKey(Template)


class Node(models.Model):
    name = models.CharField(max_length=50, unique=True,
                            verbose_name=_('name'))
    CPU = models.IntegerField(help_text=_('CPU cores.'))
    RAM = models.IntegerField(help_text=_('Mebibytes of memory.'))
    priority = models.IntegerField(help_text=_('node usage priority'))
    host = models.ForeignKey(Host)
    online = models.BooleanField(default=False)


class InstanceTemplate(models.Model, TimeStampedModel,
                       BaseResourceConfigModel):
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
      * time of creation and last modification
      * ownership information
    """
    STATES = [('NEW', _('new')),  # template has just been created
              ('SAVING', _('saving')),  # changes are being saved
              ('READY', _('ready'))]  # template is ready for instantiation
    ACCESS_METHODS = [('rdp', 'rdp'), ('nx', 'nx'), ('ssh', 'ssh'), ]
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
    state = models.CharField(max_length=10, choices=TEMPLATE_STATES,
                             default='NEW')
    images = models.ManyToManyField(Image, verbose_name=_('images'),
                                    related_name='template_set')
    # TODO review
    owner = models.ForeignKey(User, verbose_name=_('owner'),
                              related_name='template_set')

    class Meta:
        verbose_name = _('template')
        verbose_name_plural = _('templates')
        ordering = ['name', ]

    def __unicode__(self):
        return self.name

    def running_instances(self):
        """Returns the number of running instances of the template.
        """
        return self.instance_set.exclude(state='DONE').count()

    @property
    def os_type(self):
        """Get the type of the template's operating system.
        """
        if self.access_method == 'rdp':
            return "win"
        else:
            return "linux"


class Instance(models.Model, TimeStampedModel, BaseResourceConfigModel):
    """Virtual machine instance.

    Every instance has:
      * a name and a description
      * an optional parent template
      * associated share
      * a generated password for login authentication
      * time of deletion and time of suspension
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
    name = models.CharField(max_length=100, verbose_name=_('name'),
                            blank=True)
    description = models.TextField(verbose_name=_('description'),
                                   blank=True)
    template = models.ForeignKey(Template, verbose_name=_('template'),
                                 related_name='instance_set',
                                 null=True, blank=True)
    pw = models.CharField(max_length=20, verbose_name=_('password'),
                          help_text=_('Original password of instance'))
    time_of_suspend = models.DateTimeField(default=None,
                                           verbose_name=_('time of suspend'),
                                           null=True, blank=True)
    time_of_delete = models.DateTimeField(default=None,
                                          verbose_name=_('time of delete'),
                                          null=True, blank=True)
    active_since = models.DateTimeField(null=True, blank=True,
                                        verbose_name=_('active since'),
                                        help_text=_('Time stamp of '
                                                    'successful boot '
                                                    'report.'))
    share = models.ForeignKey('Share', blank=True, null=True,
                              verbose_name=_('share'),
                              related_name='instance_set')
    node = models.ForeignKey(Node, verbose_name=_('host nose'),
                             related_name='instance_set')
    state = models.CharField(max_length=20, choices=STATES,
                             default='NOSTATE')
    operation = models.CharField(max_length=100, null=True, blank=True
                                 verbose_name=_('operation'))
    # TODO review fields below
    owner = models.ForeignKey(User, verbose_name=_('owner'),
                              related_name='instance_set')

    class Meta:
        verbose_name = _('instance')
        verbose_name_plural = _('instances')
        ordering = ['pk', ]

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('one.views.vm_show', None, {'iid': self.id})
    
    @property
    def primary_host(self):
        if not hosts.exists():
            return None
        hs = hosts.filter(ipv6__is_null=False)
        if hs.exists():
            return hs[0]
        hs = hosts.filter(shared_ip=False)
        if hs.exists():
            return hs[0]
        return hosts.all()[0]

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
        """Uptime of the instance."""
        from datetime import datetime, timedelta
        if self.active_since:
            return (datetime.now().replace(tzinfo=None) -
                    self.active_since.replace(tzinfo=None))
        else:
            return timedelta()

    def get_age(self):
        """Deprecated. Use uptime instead.
        
        Get age of VM in seconds.
        """
        return self.uptime.seconds

    @property
    def waiting(self):
        return self.operation is not None

    def get_port(self, use_ipv6=False):
        """Get public port number for default access method."""
        # TODO move PROTOS to config
        PROTOS = {"rdp": (3389,'tcp'), "nx": (22,'tcp'), "ssh": (22,'tcp')}
        (port, proto) = PROTOS[self.template.access_method]
        if self.primary_host:
            endpoints = self.primary_host.get_public_endpoints(port, proto)
            endpoint = endpoints['ipv6'] if use_ipv6 else endpoints['ipv4']
            return endpoint[1] if endpoint else None
        else:
            return None

    def get_connect_host(self, use_ipv6=False):
        """Get public hostname."""
        if self.firewall_host is None:
            return _('None')
        proto = 'ipv6' if use_ipv6 else 'ipv4'
        return self.firewall_host.get_hostname(proto=proto)

    def get_connect_uri(self, use_ipv6=False):
        """Get access parameters in URI format."""
        try:
            proto = self.template.access_type
            if proto == 'ssh':
                proto = 'sshterm'
            port = self.get_port(use_ipv6=use_ipv6)
            host = self.get_connect_host(use_ipv6=use_ipv6)
            pw = self.pw
            return ("%(proto)s:cloud:%(pw)s:%(host)s:%(port)d" %
                    {"port": port, "proto": proto, "pw": pw,
                     "host": host})
        except:
            return

    @staticmethod
    def _create_context(pw, hostname, smb_password, ssh_private_key, owner,
                        token, extra):
        """Return XML context configuration with given parameters."""
        ctx = u'''
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
        return ctx

    def _create_host(self, hostname, occi_result):
        """Create firewall host for recently submitted Instance."""
        host = Host(
            vlan=Vlan.objects.get(name=self.template.network.name),
            owner=self.owner, hostname=hostname,
            mac=occi_result['interfaces'][0]['mac'],
            ipv4=occi_result['interfaces'][0]['ip'], ipv6='auto',
        )

        if self.template.network.nat:
            host.pub_ipv4 = Vlan.objects.get(
                name=self.template.network.name).snat_ip
            host.shared_ip = True

        try:
            host.save()
        except:
            for i in Host.objects.filter(ipv4=host.ipv4).all():
                logger.warning('Delete orphan fw host (%s) of %s.' % (i, self))
                i.delete()
            for i in Host.objects.filter(mac=host.mac).all():
                logger.warning('Delete orphan fw host (%s) of %s.' % (i, self))
                i.delete()
            host.save()

        host.enable_net()
        port = {"rdp": 3389, "nx": 22, "ssh": 22}[self.template.access_type]
        host.add_port("tcp", self.get_port(), port)
        self.firewall_host = host
        self.save()

    @classmethod
    def submit(cls, template, owner, extra="", share=None):
        """Submit a new instance to OpenNebula."""
        inst = Instance(pw=pwgen(), template=template, owner=owner,
                        share=share, state='PENDING', waiting=True)
        inst.save()
        hostname = u"%d" % (inst.id, )
        token = signing.dumps(inst.id, salt='activate')
        try:
            details = owner.cloud_details
        except:
            details = UserCloudDetails(user=owner)
            details.save()

        ctx = cls._create_context(inst.pw, hostname, details.smb_password,
                                  details.ssh_private_key, owner.username,
                                  token, extra)
        try:
            from .tasks import CreateInstanceTask
            x = CreateInstanceTask.delay(
                name=u"%s %d" % (owner.username, inst.id),
                instance_type=template.instance_type.name,
                disk_id=int(template.disk.id),
                network_id=int(template.network.id),
                ctx=ctx,
            )
            res = x.get(timeout=10)
            res['one_id']
        except:
            inst.delete()
            raise Exception("Unable to create VM instance.")

        inst.one_id = res['one_id']
        inst.ip = res['interfaces'][0]['ip']
        inst.name = ("%(neptun)s %(template)s (%(id)d)" %
                     {'neptun': owner.username, 'template': template.name,
                      'id': inst.one_id})
        inst.save()

        inst._create_host(hostname, res)
        return inst

    def one_delete(self):
        """Delete host in OpenNebula."""
        if self.template.state != "DONE":
            self.check_if_is_save_as_done()
        if self.one_id and self.state != 'DONE':
            self.waiting = True
            self.save()
            from .tasks import DeleteInstanceTask
            DeleteInstanceTask.delay(one_id=self.one_id)
        self.firewall_host_delete()

    def firewall_host_delete(self):
        if self.firewall_host:
            h = self.firewall_host
            self.firewall_host = None
            try:
                self.save()
            except:
                pass
            h.delete()

    def _change_state(self, new_state):
        """Change host state in OpenNebula."""
        from .tasks import ChangeInstanceStateTask
        ChangeInstanceStateTask.delay(one_id=self.one_id, new_state=new_state)
        self.waiting = True
        self.save()

    def stop(self):
        self._change_state("STOPPED")

    def resume(self):
        self._change_state("RESUME")

    def poweroff(self):
        self._change_state("POWEROFF")

    def restart(self):
        self._change_state("RESET")
        self.waiting = False
        self.save()

    def renew(self, which='both'):
        if which in ['suspend', 'both']:
            self.time_of_suspend = self.share_type['suspendx']
        if which in ['delete', 'both']:
            self.time_of_delete = self.share_type['deletex']
        if not (which in ['suspend', 'delete', 'both']):
            raise ValueError('No such expiration type.')
        self.save()

    @property
    def share_type(self):
        if self.share:
            return self.share.get_type()
        else:
            return Share.extend_type(DEFAULT_TYPE)

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


def delete_instance_pre(sender, instance, using, **kwargs):
    if instance.state != 'DONE':
        instance.one_delete()

pre_delete.connect(delete_instance_pre, sender=Instance,
                   dispatch_uid="delete_instance_pre")
