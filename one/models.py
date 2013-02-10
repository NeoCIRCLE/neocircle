# coding=utf-8
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core import signing
from django.db import models
from django.db import transaction
from django.db.models.signals import post_save
from django import forms
from django.utils.translation import ugettext_lazy as _
from firewall.models import Host, Rule, Vlan
from firewall.tasks import reload_firewall_lock
from one.util import keygen
from school.models import Person, Group
from datetime import timedelta as td
from django.db.models.signals import post_delete, pre_delete
from store.api import StoreApi

import subprocess, tempfile, os, stat, re, base64, struct

pwgen = User.objects.make_random_password

"""
User creation hook: create cloud details object
"""
def create_user_profile(sender, instance, created, **kwargs):
    if created:
            d = UserCloudDetails(user=instance)
            d.clean()
            d.save()
post_save.connect(create_user_profile, sender=User)


"""
Cloud related details of a user
"""
class UserCloudDetails(models.Model):
    user = models.ForeignKey(User, null=False, blank=False, unique=True, verbose_name=_('user'))
    smb_password = models.CharField(max_length=20,
            verbose_name=_('Samba password'),
            help_text=_('Generated password for accessing store from Windows.'))
    ssh_key = models.ForeignKey('SshKey', null=True, verbose_name=_('SSH key (public)'),
            help_text=_('Generated SSH public key for accessing store from Linux.'))
    ssh_private_key = models.TextField(verbose_name=_('SSH key (private)'), null=True,
            help_text=_('Generated SSH private key for accessing store from Linux.'))
    share_quota = models.IntegerField(verbose_name=_('share quota'), default=100)
    instance_quota = models.IntegerField(verbose_name=_('instance quota'), default=20)
    disk_quota = models.IntegerField(verbose_name=_('disk quota'), default=2048,
            help_text=_('Disk quota in mebibytes.'))

    """
    Delete old SSH key pair and generate new one.
    """
    def reset_keys(self):
        pri, pub = keygen()
        self.ssh_private_key = pri

        try:
            self.ssh_key.key = pub
        except:
            self.ssh_key = SshKey(user=self.user, key=pub)
        self.ssh_key.save()
        self.ssh_key_id = self.ssh_key.id
        self.save()

    """
    Generate new Samba password.
    """
    def reset_smb(self):
        self.smb_password = pwgen()

    def get_weighted_instance_count(self):
        c = 0
        for i in self.user.instance_set.all():
            if i.state in ('ACTIVE', 'PENDING', ):
                c = c + i.template.instance_type.credit
        return c
    def get_instance_pc(self):
        return 100*self.get_weighted_instance_count()/self.instance_quota

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
        #Create user
        if not StoreApi.createuser(instance.user.username, password, key_list, quota):
            pass
    else:
        StoreApi.set_quota(instance.user.username, instance.disk_quota*1024)
post_save.connect(set_quota, sender=UserCloudDetails)

def reset_keys(sender, instance, created, **kwargs):
    if created:
        instance.reset_smb()
        instance.reset_keys()

post_save.connect(reset_keys, sender=UserCloudDetails)

"""
Validate OpenSSH keys (length and type).
"""
class OpenSshKeyValidator(object):
    valid_types = ['ssh-rsa', 'ssh-dsa']

    def __init__(self, types=None):
        if types is not None:
            self.valid_types = types

    def __call__(self, value):
        try:
            value = "%s comment" % value
            type, key_string, comment = value.split(None, 2)
            if type not in self.valid_types:
                raise ValidationError(_('OpenSSH key type %s is not supported.') % type)
            data = base64.decodestring(key_string)
            int_len = 4
            str_len = struct.unpack('>I', data[:int_len])[0]
            if not data[int_len:int_len+str_len] == type:
                raise
        except ValidationError:
            raise
        except:
            raise ValidationError(_('Invalid OpenSSH public key.'))

"""
SSH public key (in OpenSSH format).
"""
class SshKey(models.Model):
    user = models.ForeignKey(User, null=False, blank=False)
    key = models.CharField(max_length=2000, verbose_name=_('SSH key'),
            help_text=_('<a href="/info/ssh/">SSH public key in OpenSSH format</a> used for shell and store login '
                '(2048+ bit RSA preferred). Example: <code>ssh-rsa AAAAB...QtQ== '
                'john</code>.'), validators=[OpenSshKeyValidator()])

    def __unicode__(self):
        try:
            keycomment = self.key.split(None, 2)[2]
        except:
            keycomment = _("unnamed")

        return u"%s (%s)" % (keycomment, self.user)

TEMPLATE_STATES = (("INIT", _('init')), ("PREP", _('perparing')), ("SAVE", _('saving')), ("READY", _('ready')))


TYPES = {"LAB": {"verbose_name": _('lab'),         "id": "LAB",     "suspend": td(hours=5),  "delete": td(days=15),    "help_text": _('For lab or home work with short life time.')},
         "PROJECT": {"verbose_name": _('project'), "id": "PROJECT", "suspend": td(weeks=5),  "delete": td(days=366/2), "help_text": _('For project work.')},
         "SERVER": {"verbose_name": _('server'),   "id": "SERVER",  "suspend": td(days=365), "delete": None,           "help_text": _('For long term server use.')},
         }
TYPES_L = sorted(TYPES.values(), key=lambda m: m["suspend"])
TYPES_C = tuple([(i[0], i[1]["verbose_name"]) for i in TYPES.items()])
class Share(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_('name'))
    description = models.TextField(verbose_name=_('description'))
    template = models.ForeignKey('Template', null=False, blank=False)
    group = models.ForeignKey(Group, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('created at'))
    type = models.CharField(choices=TYPES_C, max_length=10, blank=False, null=False)
    instance_limit = models.IntegerField(verbose_name=_('instance limit'),
            help_text=_('Maximal count of instances launchable for this share.'))
    per_user_limit = models.IntegerField(verbose_name=_('per user limit'),
            help_text=_('Maximal count of instances launchable by a single user.'))

"""
Virtual disks automatically synchronized with OpenNebula.
"""
class Disk(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_('name'))

    """
    Get and register virtual disks from OpenNebula.
    """
    @classmethod
    def update(cls):
        import subprocess
        proc = subprocess.Popen(["/opt/occi.sh",
        "storage", "list"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
            Disk.objects.exclude(id__in=l).delete()

    def __unicode__(self):
        return u"%s (#%d)" % (self.name, self.id)

    class Meta:
        ordering = ['name']

"""
Virtual networks automatically synchronized with OpenNebula.
"""
class Network(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_('name'))
    nat = models.BooleanField(verbose_name=_('NAT'), help_text=_('If network address translation is done.'))
    public = models.BooleanField(verbose_name=_('public'), help_text=_('If internet gateway is available.'))

    """
    Get and register virtual networks from OpenNebula.
    """
    @classmethod
    def update(cls):
        import subprocess
        proc = subprocess.Popen(["/opt/occi.sh",
        "network", "list"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
            cls.objects.exclude(id__in=l).delete()

    def __unicode__(self):
        return self.name
    class Meta:
        ordering = ['name']

"""
Instance types in OCCI configuration (manually synchronized).
"""
class InstanceType(models.Model):
    name = models.CharField(max_length=100, unique=True,
            verbose_name=_('name'))
    CPU = models.IntegerField(help_text=_('CPU cores.'))
    RAM = models.IntegerField(help_text=_('Mebibytes of memory.'))
    credit = models.IntegerField(verbose_name=_('credits'),
            help_text=_('Price of instance.'))
    def __unicode__(self):
        return u"%s" % self.name
    class Meta:
        ordering = ['credit']

TEMPLATE_STATES = (('NEW', _('new')), 
                   ('SAVING', _('saving')), ('READY', _('ready')), )
"""
Virtual machine template specifying OS, disk, type and network.
"""
class Template(models.Model):
    name = models.CharField(max_length=100, unique=True,
            verbose_name=_('name'))
    access_type = models.CharField(max_length=10,
            choices=[('rdp', 'rdp'), ('nx', 'nx'), ('ssh', 'ssh')],
            verbose_name=_('access method'))
    disk = models.ForeignKey(Disk, verbose_name=_('disk'))
    instance_type = models.ForeignKey(InstanceType, verbose_name=_('instance type'))
    network = models.ForeignKey(Network, verbose_name=_('network'))
    owner = models.ForeignKey(User, verbose_name=_('owner'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('created at'))
    state = models.CharField(max_length=10, choices=TEMPLATE_STATES, default='NEW')
    public = models.BooleanField(verbose_name=_('public'), default=False,
            help_text=_('If other users can derive templates of this one.'))
    description = models.TextField(verbose_name=_('description'), blank=True)
    system = models.TextField(verbose_name=_('operating system'), blank=True,
            help_text=(_('Name of operating system in format like "%s".') %
            "Ubuntu 12.04 LTS Desktop amd64"))

    def os_type(self):
        if self.access_type == 'rdp':
            return "win"
        else:
            return "linux"

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = _('template')
        verbose_name_plural = _('templates')

"""
Virtual machine instance.
"""
class Instance(models.Model):
    name = models.CharField(max_length=100, unique=True,
            verbose_name=_('name'), null=True, blank=True)
    ip = models.IPAddressField(blank=True, null=True, verbose_name=_('IP address'))
    template = models.ForeignKey(Template, verbose_name=_('template'))
    owner = models.ForeignKey(User, verbose_name=_('owner'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('created at'))
    state = models.CharField(max_length=20,
            choices=[('DEPLOYABLE', _('deployable')),
                ('PENDING', _('pending')),
                ('DONE', _('done')),
                ('ACTIVE', _('active')),
                ('UNKNOWN', _('unknown')),
                ('SUSPENDED', _('suspended')),
                ('FAILED', _('failed'))], default='DEPLOYABLE')
    active_since = models.DateTimeField(null=True, blank=True,
            verbose_name=_('active since'),
            help_text=_('Time stamp of successful boot report.'))
    firewall_host = models.ForeignKey(Host, blank=True, null=True, verbose_name=_('host in firewall'))
    pw = models.CharField(max_length=20, verbose_name=_('password'), help_text=_('Original password of instance'))
    one_id = models.IntegerField(unique=True, blank=True, null=True, verbose_name=_('OpenNebula ID'))
    share = models.ForeignKey('Share', blank=True, null=True, verbose_name=_('share'))
    time_of_suspend = models.DateTimeField(default=None, verbose_name=_('time of suspend'), null=True, blank=False)
    time_of_delete = models.DateTimeField(default=None, verbose_name=_('time of delete'), null=True, blank=False)
    """
    Get public port number for default access method.
    """
    def get_port(self):
        proto = self.template.access_type
        if self.template.network.nat:
            return {"rdp": 23000, "nx": 22000, "ssh": 22000}[proto] + int(self.ip.split('.')[2]) * 256 + int(self.ip.split('.')[3])
        else:
            return {"rdp": 3389, "nx": 22, "ssh": 22}[proto]
    """
    Get public hostname.
    """
    def get_connect_host(self):
        if self.template.network.nat:
            return 'cloud'
        else:
            return self.ip

    """
    Get access parameters in URI format.
    """
    def get_connect_uri(self):
        try:
            proto = self.template.access_type
            if proto == 'ssh':
                proto = 'sshterm'
            port = self.get_port()
            host = self.get_connect_host()
            pw = self.pw
            return "%(proto)s:cloud:%(pw)s:%(host)s:%(port)d" % {"port": port,
                                                "proto": proto, "host": self.firewall_host.pub_ipv4, "pw": pw}
        except:
            return

    def __unicode__(self):
        return self.name

    """
    Get and update VM state from OpenNebula.
    """
    def update_state(self):
        import subprocess

        if not self.one_id:
            return
        proc = subprocess.Popen(["/opt/occi.sh",
        "compute", "show",
        "%d"%self.one_id], stdout=subprocess.PIPE)
        (out, err) = proc.communicate()
        x = None
        try:
            from xml.dom.minidom import parse, parseString
            x = parseString(out)
            self.vnet_ip = x.getElementsByTagName("IP")[0].childNodes[0].nodeValue.split('.')[3]
            state = x.getElementsByTagName("STATE")[0].childNodes[0].nodeValue
            self.state = state
        except:
            self.state = 'UNKNOWN'
        self.save()
        return x

    """
    Get age of VM in seconds.
    """
    def get_age(self):
        from datetime import datetime
        age = 0
        try:
            age = (datetime.now().replace(tzinfo=None)
                - self.active_since.replace(tzinfo=None)).seconds
        except:
            pass
        return age

    @models.permalink
    def get_absolute_url(self):
            return ('vm_show', None, {'iid':self.id})

    """
    Submit a new instance to OpenNebula.
    """
    @classmethod
    def submit(cls, template, owner, extra=""):
        from django.template.defaultfilters import escape
        out = ""
        inst = Instance(pw=pwgen(), template=template, owner=owner)
        inst.save()
        with tempfile.NamedTemporaryFile(delete=False) as f:
            os.chmod(f.name, stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IROTH)
            token = signing.dumps(inst.id, salt='activate')
            try:
                details = owner.userclouddetails_set.all()[0]
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
                        <HOSTNAME>cloud-$VMID</HOSTNAME>
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
                                 "smbpw": escape(details.smb_password),
                                 "sshkey": escape(details.ssh_private_key),
                                 "neptun": escape(owner.username),
                                 "booturl": "https://cloud.ik.bme.hu/b/%s/" % token,
                                 "extra": extra}
            f.write(tpl)
            f.close()
            import subprocess
            proc = subprocess.Popen(["/opt/occi.sh",
                       "compute", "create",
                       f.name], stdout=subprocess.PIPE)
            (out, err) = proc.communicate()
            os.unlink(f.name)
        from xml.dom.minidom import parse, parseString
        try:
            x = parseString(out)
        except:
            raise Exception("Unable to create VM instance.")
        inst.one_id = int(x.getElementsByTagName("ID")[0].childNodes[0].nodeValue)
        inst.ip = x.getElementsByTagName("IP")[0].childNodes[0].nodeValue
        inst.name = "%(neptun)s %(template)s (%(id)d)" % {'neptun': owner.username, 'template': template.name, 'id': inst.one_id}
        inst.save()
        inst.update_state()
        host = Host(vlan=Vlan.objects.get(name=template.network.name), owner=owner, shared_ip=True)
        host.hostname = u"id-%d_user-%s" % (inst.id, owner.username)
        host.mac = x.getElementsByTagName("MAC")[0].childNodes[0].nodeValue
        host.ipv4 = inst.ip
        host.pub_ipv4 = Vlan.objects.get(name=template.network.name).snat_ip
        host.ipv6 = "auto"
        host.save()
        host.enable_net()
        host.add_port("tcp", inst.get_port(), {"rdp": 3389, "nx": 22, "ssh": 22}[inst.template.access_type])
        inst.firewall_host=host
        inst.save()
        reload_firewall_lock()
        return inst

    """
    Delete host in OpenNebula.
    """
    def one_delete(self):
        proc = subprocess.Popen(["/opt/occi.sh", "compute",
               "delete", "%d"%self.one_id], stdout=subprocess.PIPE)
        (out, err) = proc.communicate()
        if self.firewall_host:
            self.firewall_host.delete()
        reload_firewall_lock()

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
            proc = subprocess.Popen(["/opt/occi.sh",
                       "compute", "update",
                       f.name], stdout=subprocess.PIPE)
            (out, err) = proc.communicate()
            os.unlink(f.name)
            print "out: " + out

    """
    Change host state in OpenNebula.
    """
    def _change_state(self, new_state):
        self._update_vm("<STATE>" + new_state + "</STATE>")

    def stop(self):
        self._change_state("STOPPED")
    def resume(self):
        self._change_state("RESUME")
    def poweroff(self):
        self._change_state("POWEROFF")
    def restart(self):
        self._change_state("RESET")
    def save_as(self):
        """
        Save image and shut down.
        """
        imgname = "template-%d-%d" % (self.template.id, self.id)
        self._update_vm('<DISK id="0"><SAVE_AS name="%s"/></DISK>' % imgname)
        self._change_state("SHUTDOWN")
        t = self.template
        t.state = 'SAVING'
        t.save()
    def check_if_is_save_as_done(self):
        self.update_state()
        if self.state != 'DONE':
            return False
        Disk.update()
        imgname = "template-%d-%d" % (self.template.id, self.id)
        disks = Disk.objects.filter(name=imgname)
        if len(disks) != 1:
            return false
        self.template.disk_id = disks[0].id
        self.template.state = 'READY'
        self.template.save()
        self.firewall_host.delete()
        return True


    class Meta:
        verbose_name = _('instance')
        verbose_name_plural = _('instances')

def delete_instance(sender, instance, using, **kwargs):
    if instance.state != "DONE":
        instance.one_delete()
    try:
        instance.firewall_host.delete()
    except:
        pass
post_delete.connect(delete_instance, sender=Instance, dispatch_uid="delete_instance")

def delete_instance_pre(sender, instance, using, **kwargs):
    try:
        if instance.template.state != "DONE":
            instance.check_if_is_save_as_done()
    except:
        pass
pre_delete.connect(delete_instance_pre, sender=Instance, dispatch_uid="delete_instance_pre")

