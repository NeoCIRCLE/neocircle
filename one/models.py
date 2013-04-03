# coding=utf-8

from datetime import datetime
from datetime import timedelta as td
import subprocess, tempfile, os, stat, re, base64, struct, logging

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core import signing
from django.db import models
from django.db import transaction
from django.db.models.signals import post_delete, pre_delete
from django.db.models.signals import post_save
from django import forms
from django.utils.translation import ugettext_lazy as _

from firewall.models import Host, Rule, Vlan, Record
from school.models import Person, Group
from store.api import StoreApi
from .util import keygen
from cloud.settings import CLOUD_URL

logger = logging.getLogger(__name__)
pwgen = User.objects.make_random_password

def create_user_profile(sender, instance, created, **kwargs):
    """User creation hook: create cloud details object"""
    if created:
        d = UserCloudDetails(user=instance)
        d.clean()
        d.save()

post_save.connect(create_user_profile, sender=User)

class UserCloudDetails(models.Model):
    """Cloud related details of a user."""
    user = models.OneToOneField(User, verbose_name=_('user'),
            related_name='cloud_details')
    smb_password = models.CharField(max_length=20,
            verbose_name=_('Samba password'),
            help_text=_('Generated password for accessing store from '
                'Windows.'))
    ssh_key = models.ForeignKey('SshKey', verbose_name=_('SSH key (public)'),
            null=True, blank=True, related_name='userclouddetails_set',
            help_text=_('Generated SSH public key for accessing store from '
                    'Linux.'))
    ssh_private_key = models.TextField(verbose_name=_('SSH key (private)'),
            blank=True, help_text=_('Generated SSH private key for '
                    'accessing store from Linux.'))
    share_quota = models.IntegerField(verbose_name=_('share quota'),
            default=0)
    instance_quota = models.IntegerField(verbose_name=_('instance quota'),
            default=20)
    disk_quota = models.IntegerField(verbose_name=_('disk quota'),
            default=2048, help_text=_('Disk quota in mebibytes.'))

    def reset_keys(self):
        """Delete old SSH key pair and generate new one."""
        pri, pub = keygen()
        self.ssh_private_key = pri

        try:
            self.ssh_key.key = pub
        except:
            self.ssh_key = SshKey(user=self.user, key=pub)
        self.ssh_key.save()
        self.ssh_key_id = self.ssh_key.id
        self.save()

    def reset_smb(self):
        """Generate new Samba password."""
        self.smb_password = pwgen()

    def get_weighted_instance_count(self):
        c = 0
        for i in self.user.instance_set.all():
            if i.state in ('ACTIVE', 'PENDING', ):
                c = c + i.template.instance_type.credit
        return c
    def get_instance_pc(self):
        return 100 * self.get_weighted_instance_count() / self.instance_quota
    def get_weighted_share_count(self):
        c = 0
        for i in Share.objects.filter(owner=self.user).all():
            c = c + i.template.instance_type.credit * i.instance_limit
        return c
    def get_share_pc(self):
        return 100 * self.get_weighted_share_count() / self.share_quota

def set_quota(sender, instance, created, **kwargs):
    if not StoreApi.userexist(instance.user.username):
        try:
            password = instance.smb_password
            quota = instance.disk_quota * 1024
            key_list = []
            for key in instance.user.sshkey_set.all():
                key_list.append(key.key)
        except:
            pass
        # Create user
        if not StoreApi.createuser(instance.user.username, password,
                key_list, quota):
            pass
    else:
        StoreApi.set_quota(instance.user.username,
                instance.disk_quota * 1024)
post_save.connect(set_quota, sender=UserCloudDetails)

def reset_keys(sender, instance, created, **kwargs):
    if created:
        instance.reset_smb()
        instance.reset_keys()

post_save.connect(reset_keys, sender=UserCloudDetails)

class OpenSshKeyValidator(object):
    """Validate OpenSSH keys (length and type)."""
    valid_types = ['ssh-rsa', 'ssh-dsa']

    def __init__(self, types=None):
        if types is not None:
            self.valid_types = types

    def __call__(self, value):
        try:
            value = "%s comment" % value
            type, key_string, comment = value.split(None, 2)
            if type not in self.valid_types:
                raise ValidationError(_('OpenSSH key type %s is not '
                    'supported.') % type)
            data = base64.decodestring(key_string)
            int_len = 4
            str_len = struct.unpack('>I', data[:int_len])[0]
            if not data[int_len:int_len+str_len] == type:
                raise
        except ValidationError:
            raise
        except:
            raise ValidationError(_('Invalid OpenSSH public key.'))

class SshKey(models.Model):
    """SSH public key (in OpenSSH format)."""
    user = models.ForeignKey(User, related_name='sshkey_set')
    key = models.TextField(verbose_name=_('SSH key'),
            help_text=_('<a href="/info/ssh/">SSH public key in OpenSSH '
                    'format</a> used for shell and store login '
                    '(2048+ bit RSA preferred). Example: '
                    '<code>ssh-rsa AAAAB...QtQ== john</code>.'),
            validators=[OpenSshKeyValidator()])

    def __unicode__(self):
        try:
            keycomment = self.key.split(None, 2)[2]
        except:
            keycomment = _("unnamed")

        return u"%s (%s)" % (keycomment, self.user)

TEMPLATE_STATES = (("INIT", _('init')), ("PREP", _('perparing')),
        ("SAVE", _('saving')), ("READY", _('ready')))

TYPES = {"LAB": {"verbose_name": _('lab'), "id": "LAB",
                 "suspend": td(hours=5), "delete": td(days=15),
                 "help_text": _('For lab or homework with short lifetime.')},
         "PROJECT": {"verbose_name": _('project'), "id": "PROJECT",
                     "suspend": td(weeks=5), "delete": td(days=366/2),
                     "help_text": _('For project work.')},
         "SERVER": {"verbose_name": _('server'), "id": "SERVER",
                    "suspend": td(days=365), "delete": None,
                    "help_text": _('For long-term server use.')},
         }
TYPES_L = sorted(TYPES.values(), key=lambda m: m["suspend"])
TYPES_C = tuple([(i[0], i[1]["verbose_name"]) for i in TYPES.items()])

class Share(models.Model):
    name = models.CharField(max_length=100, verbose_name=_('name'))
    description = models.TextField(verbose_name=_('description'))
    template = models.ForeignKey('Template', related_name='share_set')
    group = models.ForeignKey(Group, related_name='share_set')
    created_at = models.DateTimeField(auto_now_add=True,
            verbose_name=_('created at'))
    type = models.CharField(choices=TYPES_C, max_length=10)
    instance_limit = models.IntegerField(verbose_name=_('instance limit'),
            help_text=_('Maximal count of instances launchable for this '
                'share.'))
    per_user_limit = models.IntegerField(verbose_name=_('per user limit'),
            help_text=_('Maximal count of instances launchable by a single '
                'user.'))
    owner = models.ForeignKey(User, null=True, blank=True, related_name='share_set')

    class Meta:
        ordering = ['group', 'template', 'owner', ]
        verbose_name = _('share')
        verbose_name_plural = _('shares')

    def get_type(self):
        t = TYPES[self.type]
        t['deletex'] = (datetime.now() + td(seconds=1) + t['delete']
                if t['delete'] else None)
        t['suspendx'] = (datetime.now() + td(seconds=1) + t['suspend']
                if t['suspend'] else None)
        return t
    def get_running_or_stopped(self, user=None):
        running = (Instance.objects.all().exclude(state='DONE')
            .filter(share=self))
        if user:
            return running.filter(owner=user).count()
        else:
            return running.count()

    def get_running(self, user=None):
        running = (Instance.objects.all().exclude(state='DONE')
            .exclude(state='STOPPED').filter(share=self))
        if user:
            return running.filter(owner=user).count()
        else:
            return running.count()

    def get_instance_pc(self):
        return float(self.get_running()) / self.instance_limit * 100

    def __unicode__(self):
        return u"%(group)s: %(tpl)s %(owner)s" % {
                'group': self.group, 'tpl': self.template, 'owner': self.owner}

class Disk(models.Model):
    """Virtual disks automatically synchronized with OpenNebula."""
    name = models.CharField(max_length=100, unique=True,
            verbose_name=_('name'))

    class Meta:
        ordering = ['name']
        verbose_name = _('disk')
        verbose_name_plural = _('disks')

    def __unicode__(self):
        return u"%s (#%d)" % (self.name, self.id)

    @staticmethod
    def update(delete=True):
        """Get and register virtual disks from OpenNebula."""
        import subprocess
        proc = subprocess.Popen(["/opt/occi.sh", "storage", "list"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = proc.communicate()
        from xml.dom.minidom import parse, parseString
        x = parseString(out)
        with transaction.commit_on_success():
            l = []
            for d in x.getElementsByTagName("STORAGE"):
                id = int(d.getAttributeNode('href').nodeValue.split('/')[-1])
                name=d.getAttributeNode('name').nodeValue
                try:
                    d = Disk.objects.get(id=id)
                    d.name=name
                    d.save()
                except:
                    Disk(id=id, name=name).save()
                l.append(id)
            if delete:
                Disk.objects.exclude(id__in=l).delete()

class Network(models.Model):
    """Virtual networks automatically synchronized with OpenNebula."""
    name = models.CharField(max_length=100, unique=True,
            verbose_name=_('name'))
    nat = models.BooleanField(verbose_name=_('NAT'),
            help_text=_('If network address translation is done.'))
    public = models.BooleanField(verbose_name=_('public'),
            help_text=_('If internet gateway is available.'))

    class Meta:
        ordering = ['name']
        verbose_name = _('network')
        verbose_name_plural = _('networks')


    def __unicode__(self):
        return self.name

    @staticmethod
    def update():
        """Get and register virtual networks from OpenNebula."""
        import subprocess
        proc = subprocess.Popen(["/opt/occi.sh", "network", "list"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = proc.communicate()
        from xml.dom.minidom import parse, parseString
        x = parseString(out)
        with transaction.commit_on_success():
            l = []
            for d in x.getElementsByTagName("NETWORK"):
                id = int(d.getAttributeNode('href').nodeValue.split('/')[-1])
                name=d.getAttributeNode('name').nodeValue
                try:
                    n = Network.objects.get(id=id)
                    n.name = name
                    n.save()
                except:
                    Network(id=id, name=name).save()
                l.append(id)
            Network.objects.exclude(id__in=l).delete()


class InstanceType(models.Model):
    """Instance types in OCCI configuration (manually synchronized)."""
    name = models.CharField(max_length=100, unique=True,
            verbose_name=_('name'))
    CPU = models.IntegerField(help_text=_('CPU cores.'))
    RAM = models.IntegerField(help_text=_('Mebibytes of memory.'))
    credit = models.IntegerField(verbose_name=_('credits'),
            help_text=_('Price of instance.'))

    class Meta:
        ordering = ['credit']
        verbose_name  = _('instance type')
        verbose_name_plural = _('instance types')

    def __unicode__(self):
        return u"%s" % self.name

TEMPLATE_STATES = (('NEW', _('new')), ('SAVING', _('saving')),
                   ('READY', _('ready')), )
class Template(models.Model):
    """Virtual machine template specifying OS, disk, type and network."""
    name = models.CharField(max_length=100, unique=True,
            verbose_name=_('name'))
    access_type = models.CharField(max_length=10,
            choices=[('rdp', 'rdp'), ('nx', 'nx'), ('ssh', 'ssh')],
            verbose_name=_('access method'))
    disk = models.ForeignKey(Disk, verbose_name=_('disk'), related_name='template_set')
    instance_type = models.ForeignKey(InstanceType, related_name='template_set',
            verbose_name=_('instance type'))
    network = models.ForeignKey(Network, verbose_name=_('network'),
            related_name='template_set')
    owner = models.ForeignKey(User, verbose_name=_('owner'),
            related_name='template_set')
    created_at = models.DateTimeField(auto_now_add=True,
            verbose_name=_('created at'))
    state = models.CharField(max_length=10, choices=TEMPLATE_STATES,
            default='NEW')
    public = models.BooleanField(verbose_name=_('public'), default=False,
            help_text=_('If other users can derive templates of this one.'))
    description = models.TextField(verbose_name=_('description'), blank=True)
    system = models.TextField(verbose_name=_('operating system'), blank=True,
            help_text=(_('Name of operating system in format like "%s".') %
            "Ubuntu 12.04 LTS Desktop amd64"))

    class Meta:
        verbose_name = _('template')
        verbose_name_plural = _('templates')
        ordering = ['name', ]


    def __unicode__(self):
        return self.name

    def running_instances(self):
        return self.instance_set.exclude(state='DONE').count()

    @property
    def os_type(self):
        if self.access_type == 'rdp':
            return "win"
        else:
            return "linux"

    @transaction.autocommit
    def safe_delete(self):
        if not self.instance_set.exclude(state='DONE').exists():
            self.delete()
            return True
        else:
            logger.info("Could not delete template. Instances still running!")
            return False

class Instance(models.Model):
    """Virtual machine instance."""
    name = models.CharField(max_length=100,
            verbose_name=_('name'), blank=True)
    ip = models.IPAddressField(blank=True, null=True,
            verbose_name=_('IP address'))
    template = models.ForeignKey(Template, verbose_name=_('template'),
            related_name='instance_set')
    owner = models.ForeignKey(User, verbose_name=_('owner'),
            related_name='instance_set')
    created_at = models.DateTimeField(auto_now_add=True,
            verbose_name=_('created at'))
    state = models.CharField(max_length=20,
            choices=[('DEPLOYABLE', _('deployable')),
                     ('PENDING', _('pending')),
                     ('DONE', _('done')),
                     ('ACTIVE', _('active')),
                     ('UNKNOWN', _('unknown')),
                     ('STOPPED', _('suspended')),
                     ('FAILED', _('failed'))],
            default='DEPLOYABLE')
    active_since = models.DateTimeField(null=True, blank=True,
            verbose_name=_('active since'),
            help_text=_('Time stamp of successful boot report.'))
    firewall_host = models.ForeignKey(Host, blank=True, null=True,
            verbose_name=_('host in firewall'), related_name='instance_set')
    pw = models.CharField(max_length=20, verbose_name=_('password'),
            help_text=_('Original password of instance'))
    one_id = models.IntegerField(unique=True, blank=True, null=True,
            verbose_name=_('OpenNebula ID'))
    share = models.ForeignKey('Share', blank=True, null=True,
            verbose_name=_('share'), related_name='instance_set')
    time_of_suspend = models.DateTimeField(default=None,
            verbose_name=_('time of suspend'), null=True, blank=True)
    time_of_delete = models.DateTimeField(default=None,
            verbose_name=_('time of delete'), null=True, blank=True)
    waiting = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('instance')
        verbose_name_plural = _('instances')
        ordering = ['pk', ]

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
            return ('one.views.vm_show', None, {'iid':self.id})

    def get_port(self, use_ipv6=False):
        """Get public port number for default access method."""
        proto = self.template.access_type
        if self.template.network.nat and not use_ipv6:
            return {"rdp": 23000, "nx": 22000, "ssh": 22000}[proto] + int(self.ip.split('.')[2]) * 256 + int(self.ip.split('.')[3])
        else:
            return {"rdp": 3389, "nx": 22, "ssh": 22}[proto]
    def get_connect_host(self, use_ipv6=False):
        """Get public hostname."""
        if self.firewall_host is None:
            return _('None')
        try:
            if use_ipv6:
                return self.firewall_host.record_set.filter(type='AAAA')[0].get_data()['name']
            else:
                if self.template.network.nat:
                    ip = self.firewall_host.pub_ipv4
                    return Record.objects.filter(type='A', address=ip)[0].get_data()['name']
                else:
                    return self.firewall_host.record_set.filter(type='A')[0].get_data()['name']
        except:
            if self.template.network.nat:
                return self.firewall_host.pub_ipv4
            else:
                return self.firewall_host.ipv4

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

    def update_state(self):
        """Get and update VM state from OpenNebula."""
        import subprocess

        if not self.one_id:
            return
        proc = subprocess.Popen(["/opt/occi.sh", "compute", "show",
            "%d" % self.one_id], stdout=subprocess.PIPE)
        (out, err) = proc.communicate()
        x = None
        old_state = self.state
        try:
            from xml.dom.minidom import parse, parseString
            x = parseString(out)
            self.vnet_ip = (x.getElementsByTagName("IP")[0].childNodes[0]
                    .nodeValue.split('.')[3])
            state = x.getElementsByTagName("STATE")[0].childNodes[0].nodeValue
            self.state = state
        except:
            self.state = 'UNKNOWN'
        if self.state != old_state:
            self.waiting = False
        self.save()
        if self.template.state == 'SAVING':
            self.check_if_is_save_as_done()
        return x

    def get_age(self):
        """Get age of VM in seconds."""
        from datetime import datetime
        age = 0
        try:
            age = (datetime.now().replace(tzinfo=None)
                - self.active_since.replace(tzinfo=None)).seconds
        except:
            pass
        return age

    @classmethod
    def submit(cls, template, owner, extra="", share=None):
        """Submit a new instance to OpenNebula."""
        from django.template.defaultfilters import escape
        out = ""
        inst = Instance(pw=pwgen(), template=template, owner=owner,
                share=share, state='PENDING')
        inst.save()
        hostname = u"cloud-%d" % (inst.id, )
        with tempfile.NamedTemporaryFile(delete=False) as f:
            os.chmod(f.name, stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IROTH)
            token = signing.dumps(inst.id, salt='activate')
            try:
                details = owner.cloud_details
            except:
                details = UserCloudDetails(user=owner)
                details.save()

            tpl = u"""
                <COMPUTE>
                    <NAME>%(name)s</NAME>
                    <INSTANCE_TYPE href="http://www.opennebula.org/instance_type/%(instance)s"/>
                    <DISK>
                        <STORAGE href="http://www.opennebula.org/storage/%(disk)d"/>
                    </DISK>
                    <NIC>
                        <NETWORK href="http://www.opennebula.org/network/%(net)d"/>
                    </NIC>
                    <CONTEXT>
                        <SOURCE>web</SOURCE>
                        <HOSTNAME>%(hostname)s</HOSTNAME>
                        <NEPTUN>%(neptun)s</NEPTUN>
                        <USERPW>%(pw)s</USERPW>
                        <SMBPW>%(smbpw)s</SMBPW>
                        <SSHPRIV>%(sshkey)s</SSHPRIV>
                        <BOOTURL>%(booturl)s</BOOTURL>
                        <SERVER>store.cloud.ik.bme.hu</SERVER>
                        %(extra)s
                    </CONTEXT>
                </COMPUTE>""" % {"name": u"%s %d" % (owner.username, inst.id),
                                 "instance": template.instance_type,
                                 "disk": template.disk.id,
                                 "net": template.network.id,
                                 "pw": escape(inst.pw),
                                 "hostname": escape(hostname),
                                 "smbpw": escape(details.smb_password),
                                 "sshkey": escape(details.ssh_private_key),
                                 "neptun": escape(owner.username),
                                 "booturl": "%sb/%s/" % ( CLOUD_URL, token ),
                                 "extra": extra}
            f.write(tpl)
            f.close()
            import subprocess
            proc = subprocess.Popen(["/opt/occi.sh", "compute", "create",
                f.name], stdout=subprocess.PIPE)
            (out, err) = proc.communicate()
            os.unlink(f.name)
        from xml.dom.minidom import parse, parseString
        try:
            x = parseString(out)
        except:
            inst.delete()
            raise Exception("Unable to create VM instance.")
        inst.one_id = int(x.getElementsByTagName("ID")[0].childNodes[0]
                .nodeValue)
        inst.ip = x.getElementsByTagName("IP")[0].childNodes[0].nodeValue
        inst.name = ("%(neptun)s %(template)s (%(id)d)" %
                {'neptun': owner.username, 'template': template.name,
                 'id': inst.one_id})
        inst.save()
        host = Host(vlan=Vlan.objects.get(name=template.network.name),
                owner=owner)
        host.hostname = hostname
        host.mac = x.getElementsByTagName("MAC")[0].childNodes[0].nodeValue
        host.ipv4 = inst.ip
        if inst.template.network.nat:
            host.pub_ipv4 = Vlan.objects.get(name=template.network.name).snat_ip
            host.shared_ip = True
        host.ipv6 = "auto"
        try:
            host.save()
        except:
            for i in Host.objects.filter(ipv4=host.ipv4).all():
                logger.warning('Delete orphan fw host (%s) of %s.' % (i, inst))
                i.delete()
            for i in Host.objects.filter(mac=host.mac).all():
                logger.warning('Delete orphan fw host (%s) of %s.' % (i, inst))
                i.delete()
            host.save()
        host.enable_net()
        host.add_port("tcp", inst.get_port(), {"rdp": 3389, "nx": 22,
            "ssh": 22}[inst.template.access_type])
        inst.firewall_host=host
        inst.save()
        return inst

    def one_delete(self):
        """Delete host in OpenNebula."""
        if self.one_id and self.state != 'DONE':
            proc = subprocess.Popen(["/opt/occi.sh", "compute", "delete",
                    "%d" % self.one_id], stdout=subprocess.PIPE)
            (out, err) = proc.communicate()
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

    def _update_vm(self, template):
        out = ""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            os.chmod(f.name, stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IROTH)
            tpl = u"""
                <COMPUTE>
                    <ID>%(id)d</ID>
                    %(template)s
                </COMPUTE>""" % {"id": self.one_id,
                                 "template": template}
            f.write(tpl)
            f.close()
            import subprocess
            proc = subprocess.Popen(["/opt/occi.sh", "compute", "update",
                       f.name], stdout=subprocess.PIPE)
            (out, err) = proc.communicate()
            os.unlink(f.name)
            print "out: " + out

    def _change_state(self, new_state):
        """Change host state in OpenNebula."""
        self._update_vm("<STATE>" + new_state + "</STATE>")
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
            self.time_of_suspend = self.share.get_type()['suspendx']
        if which in ['delete', 'both']:
            self.time_of_delete = self.share.get_type()['deletex']
        if not (which in ['suspend', 'delete', 'both']):
            raise ValueError('No such expiration type.')
        self.save()

    def save_as(self):
        """Save image and shut down."""
        imgname = "template-%d-%d" % (self.template.id, self.id)
        self._update_vm('<DISK id="0"><SAVE_AS name="%s"/></DISK>' % imgname)
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

def delete_instance(sender, instance, using, **kwargs):
    if instance.state != "DONE":
        instance.one_delete()
    try:
        instance.firewall_host_delete()
    except:
        pass
post_delete.connect(delete_instance, sender=Instance,
        dispatch_uid="delete_instance")

def delete_instance_pre(sender, instance, using, **kwargs):
    try:
        if instance.template.state != "DONE":
            instance.check_if_is_save_as_done()
    except:
        pass
pre_delete.connect(delete_instance_pre, sender=Instance,
        dispatch_uid="delete_instance_pre")

