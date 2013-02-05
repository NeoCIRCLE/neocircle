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
from school.models import Person

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
    def __unicode__(self):
        return u"%s" % self.name

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
    """
    Get public port number for default access method.
    """
    def get_port(self):
        proto = self.template.access_type
        if self.template.network.nat:
            return {"rdp": 23000, "nx": 22000, "ssh": 22000}[proto] + int(self.ip.split('.')[3])
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
            if self.state == 'PENDING' and state == 'ACTIVE':
                from datetime import datetime
                self.active_since = datetime.now()
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
    def submit(cls, template, owner):
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
                    </CONTEXT>
                </COMPUTE>""" % {"name": u"%s %d" % (owner.username, inst.id),
                                 "instance": template.instance_type,
                                 "disk": template.disk.id,
                                 "net": template.network.id,
                                 "pw": escape(inst.pw),
                                 "smbpw": escape(details.smb_password),
                                 "sshkey": escape(details.ssh_private_key),
                                 "neptun": escape(owner.username),
                                 "booturl": "http://cloud.ik.bme.hu/b/%s/" % token, }
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
    def delete(self):
        proc = subprocess.Popen(["/opt/occi.sh", "compute",
               "delete", "%d"%self.one_id], stdout=subprocess.PIPE)
        (out, err) = proc.communicate()
        self.firewall_host.delete()
        reload_firewall_lock()

    """
    Change host state in OpenNebula.
    """
    def _change_state(self, new_state):
        from django.template.defaultfilters import escape
        out = ""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            os.chmod(f.name, stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IROTH)
            tpl = u"""
                <COMPUTE>
                    <ID>%(id)d</ID>
                    <STATE>%(state)s</STATE>
                </COMPUTE>""" % {"id": self.one_id,
                                 "state": new_state}
            f.write(tpl)
            f.close()
            import subprocess
            proc = subprocess.Popen(["/opt/occi.sh",
                       "compute", "update",
                       f.name], stdout=subprocess.PIPE)
            (out, err) = proc.communicate()
            os.unlink(f.name)
            print "out: " + out

    def stop(self):
        self._change_state("STOPPED")
    def resume(self):
        self._change_state("RESUME")
    def poweroff(self):
        self._change_state("POWEROFF")
    def restart(self):
        self._change_state("RESTART")


    class Meta:
        verbose_name = _('instance')
        verbose_name_plural = _('instances')
