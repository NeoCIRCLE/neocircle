# coding=utf-8
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core import signing
from django.db import models
from django.db import transaction
from django.db.models.signals import post_save
from django import forms
from django.utils.translation import ugettext_lazy as _
from one.util import keygen
from school.models import Person
import subprocess, tempfile, os, stat


pwgen = User.objects.make_random_password 

def create_user_profile(sender, instance, created, **kwargs):
    if created:
            d = UserCloudDetails(user=instance)
            d.clean()
            d.save()
post_save.connect(create_user_profile, sender=User)

class UserCloudDetails(models.Model):
    user = models.ForeignKey(User, null=False, blank=False, unique=True)
    smb_password = models.CharField(max_length=20)
    ssh_key = models.ForeignKey('SshKey', null=True)
    ssh_private_key = models.TextField()


    def reset_keys(self):
        pri, pub = keygen()
        self.ssh_private_key = pri

        try:
            self.ssh_key.key = pub
        except:
            self.ssh_key = SshKey(user=self.user, key=pub)
        self.ssh_key.save()

    def reset_smb(self):
        self.smb_password = pwgen()

    def clean(self):
        super(UserCloudDetails, self).clean()
        if not self.ssh_key:
            self.reset_keys()
            if not self.smb_password or len(self.smb_password) == 0:
                self.reset_smb()

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


class SshKey(models.Model):
    user = models.ForeignKey(User, null=False, blank=False)
    key = models.CharField(max_length=2000, verbose_name=_('SSH key'),
            help_text=_('<a href="/info/ssh/">SSH public key in OpenSSH format</a> used for shell login '
                '(2048+ bit RSA preferred). Example: <code>ssh-rsa AAAAB...QtQ== '
                'john</code>.'), validators=[OpenSshKeyValidator()])
    def __unicode__(self):
        try:
            keycomment = self.key.split(None, 2)[2]
        except:
            keycomment = _("unnamed")

        return u"%s (%s)" % (keycomment, self.user)


class Disk(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_('name'))

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


class Network(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_('name'))
    nat = models.BooleanField()
    public = models.BooleanField()
    
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
        return u"%s (vlan%03d)" % (self.name, self.id)
    class Meta:
        ordering = ['name']

class InstanceType(models.Model):
    name = models.CharField(max_length=100, unique=True,
            verbose_name=_('name'))
    CPU = models.IntegerField()
    RAM = models.IntegerField()
    def __unicode__(self):
        return u"%s" % self.name
	

class Template(models.Model):
    name = models.CharField(max_length=100, unique=True,
            verbose_name=_('név'))
    access_type = models.CharField(max_length=10, choices=[('rdp', 'rdp'), ('nx', 'nx'), ('ssh', 'ssh')])
    disk = models.ForeignKey(Disk)
    instance_type = models.ForeignKey(InstanceType)
    network = models.ForeignKey(Network)
    owner = models.ForeignKey(User)
    created_at = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = _('sablon')
        verbose_name_plural = _('sablonok')


class Instance(models.Model):
    name = models.CharField(max_length=100, unique=True,
            verbose_name=_('név'), null=True, blank=True)
    ip = models.IPAddressField(blank=True, null=True)
    template = models.ForeignKey(Template)
    owner = models.ForeignKey(User)
    created_at = models.DateTimeField(auto_now_add=True)
    state = models.CharField(max_length=20, choices=[('DEPLOYABLE', 'DEPLOYABLE'), ('PENDING', 'PENDING'), ('DONE', 'DONE'), ('ACTIVE', 'ACTIVE'),('UNKNOWN', 'UNKNOWN'), ('SUSPENDED', 'SUSPENDED'), ('FAILED', 'FAILED')], default='DEPLOYABLE')
    active_since = models.DateTimeField(null=True, blank=True)
    pw = models.CharField(max_length=20)
    one_id = models.IntegerField(unique=True, blank=True, null=True)
    def get_port(self):
        proto = self.template.access_type
        if self.template.network.nat:
            return {"rdp": 23000, "nx": 22000, "ssh": 22000}[proto] + int(self.ip.split('.')[3])
        else:
            return {"rdp": 3389, "nx": 22, "ssh": 22}[proto]
    def get_connect_host(self):
        if self.template.network.nat:
            return 'cloud'
        else:
            return self.ip
    def get_connect_uri(self):
        try:
            proto = self.template.access_type
            port = self.get_port()
            host = self.get_connect_host()
            pw = self.pw
            return "%(proto)s:cloud:%(pw)s:%(host)s:%(port)d" % {"port": port,
                                                "proto": proto, "host": host, "pw": pw}
        except:
            return

    def __unicode__(self):
        return self.name
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
            return ('vm_show', None, {'iid':self.id,})

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
                        <HOSTNAME>cloud-$VMID</HOSTNAME>
                        <NEPTUN>%(neptun)s</NEPTUN>
                        <USERPW>%(pw)s</USERPW>
                        <SMBPW>%(smbpw)s</SMBPW>
                        <SSHPRIV>%(sshkey)s</SSHPRIV>
                        <BOOTURL>%(booturl)s</BOOTURL>
                        <SERVER>152.66.243.73</SERVER>
                    </CONTEXT>
                </COMPUTE>""" % {"name": u"%s %d" % (owner.username, inst.id),
                                 "instance": template.instance_type,
                                 "disk": template.disk.id,
                                 "net": template.network.id,
                                 "pw": escape(inst.pw),
                                 "smbpw": escape(details.smb_password),
                             "sshkey": escape(details.ssh_private_key),
                             "neptun": escape(owner.username),
                             "booturl": "http://cloud.ik.bme.hu/b/%s/" % token,
                             }
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
        return inst

    def delete(self):
        proc = subprocess.Popen(["/opt/occi.sh", "compute",
               "delete", "%d"%self.one_id], stdout=subprocess.PIPE)
        (out, err) = proc.communicate()

    class Meta:
        verbose_name = _('instance')
        verbose_name_plural = _('instances')




# vim: et sw=4 ai fenc=utf8 smarttab :
