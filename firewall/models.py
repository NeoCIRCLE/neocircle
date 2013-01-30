# -*- coding: utf8 -*-

from django.contrib.auth.models import User
from django.db import models
from django.forms import fields, ValidationError
from django.utils.translation import ugettext_lazy as _
from firewall.fields import *
from south.modelsinspector import add_introspection_rules
from django.core.validators import MinValueValidator, MaxValueValidator
from modeldict import ModelDict

class Setting(models.Model):
    key = models.CharField(max_length=32)
    value = models.CharField(max_length=200)
    description = models.TextField(blank=True)

settings = ModelDict(Setting, key='key', value='value', instances=False)

class Rule(models.Model):
    CHOICES_type = (('host', 'host'), ('firewall', 'firewall'), ('vlan', 'vlan'))
    CHOICES_proto = (('tcp', 'tcp'), ('udp', 'udp'), ('icmp', 'icmp'))
    CHOICES_dir = (('0', 'out'), ('1', 'in'))

    direction = models.CharField(max_length=1, choices=CHOICES_dir, blank=False)
    description = models.TextField(blank=True)
    foreign_network = models.ForeignKey('VlanGroup', related_name="ForeignRules")
    dport = models.IntegerField(blank=True, null=True, validators=[MinValueValidator(1), MaxValueValidator(65535)])
    sport = models.IntegerField(blank=True, null=True, validators=[MinValueValidator(1), MaxValueValidator(65535)])
    proto = models.CharField(max_length=10, choices=CHOICES_proto, blank=True, null=True)
    extra = models.TextField(blank=True)
    accept = models.BooleanField(default=False)
    owner = models.ForeignKey(User, blank=True, null=True)
    r_type = models.CharField(max_length=10, choices=CHOICES_type)
    nat = models.BooleanField(default=False)
    nat_dport = models.IntegerField(blank=True, null=True, validators=[MinValueValidator(1), MaxValueValidator(65535)])
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    vlan = models.ForeignKey('Vlan', related_name="rules", blank=True, null=True)
    vlangroup = models.ForeignKey('VlanGroup', related_name="rules", blank=True, null=True)
    host = models.ForeignKey('Host', related_name="rules", blank=True, null=True)
    hostgroup = models.ForeignKey('Group', related_name="rules", blank=True, null=True)
    firewall = models.ForeignKey('Firewall', related_name="rules", blank=True, null=True)

    def __unicode__(self):
        return self.desc()

    def clean(self):
        count = 0
        for field in [self.vlan, self.vlangroup, self.host, self.hostgroup, self.firewall]:
             if field is None:
                 count = count + 1
        if count != 4:
            raise ValidationError('jaj')

    def desc(self):
        para = u""
        if(self.dport):
            para = "dport=%s %s" % (self.dport, para)
        if(self.sport):
            para = "sport=%s %s" % (self.sport, para)
        if(self.proto):
            para = "proto=%s %s" % (self.proto, para)
        return u'[' + self.r_type + u'] ' + (unicode(self.foreign_network) + u' ▸ ' + self.r_type if self.direction=='1' else self.r_type + u' ▸ ' + unicode(self.foreign_network)) + u' ' + para + u' ' +self.description

class Vlan(models.Model):
    vid = models.IntegerField(unique=True)
    name = models.CharField(max_length=20, unique=True, validators=[val_alfanum])
    prefix4 = models.IntegerField(default=16)
    prefix6 = models.IntegerField(default=80)
    interface = models.CharField(max_length=20, unique=True)
    net4 = models.GenericIPAddressField(protocol='ipv4', unique=True)
    net6 = models.GenericIPAddressField(protocol='ipv6', unique=True)
    ipv4 = models.GenericIPAddressField(protocol='ipv4', unique=True)
    ipv6 = models.GenericIPAddressField(protocol='ipv6', unique=True)
    snat_ip = models.GenericIPAddressField(protocol='ipv4', blank=True, null=True)
    snat_to = models.ManyToManyField('self', symmetrical=False, blank=True, null=True)
    description = models.TextField(blank=True)
    comment = models.TextField(blank=True)
    domain = models.TextField(blank=True, validators=[val_domain])
    dhcp_pool = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(User, blank=True, null=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.name

    def net_ipv6(self):
        return self.net6 + "/" + unicode(self.prefix6)

    def net_ipv4(self):
        return self.net4 + "/" + unicode(self.prefix4)

class VlanGroup(models.Model):
    name = models.CharField(max_length=20, unique=True)
    vlans = models.ManyToManyField('Vlan', symmetrical=False, blank=True, null=True)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(User, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.name

class Group(models.Model):
    name = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(User, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.name

class Alias(models.Model):
    host = models.ForeignKey('Host')
    alias = models.CharField(max_length=40, unique=True, validators=[val_domain])
    owner = models.ForeignKey(User, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'aliases'

class Host(models.Model):
    hostname = models.CharField(max_length=40, unique=True, validators=[val_alfanum])
    reverse = models.CharField(max_length=40, validators=[val_domain], blank=True, null=True)
    mac = MACAddressField(unique=True)
    ipv4 = models.GenericIPAddressField(protocol='ipv4', unique=True)
    pub_ipv4 = models.GenericIPAddressField(protocol='ipv4', blank=True, null=True)
    ipv6 = models.GenericIPAddressField(protocol='ipv6', unique=True, blank=True, null=True)
    shared_ip = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    comment = models.TextField(blank=True)
    location = models.TextField(blank=True)
    vlan = models.ForeignKey('Vlan')
    owner = models.ForeignKey(User)
    groups = models.ManyToManyField('Group', symmetrical=False, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.hostname

    def save(self, *args, **kwargs):
        if not self.id and self.ipv6 == "auto":
            self.ipv6 = ipv4_2_ipv6(self.ipv4)
        if not self.shared_ip and self.pub_ipv4 and Host.objects.exclude(id=self.id).filter(pub_ipv4=self.pub_ipv4):
            raise ValidationError("Ha a shared_ip be van pipalva, akkor egyedinek kell lennie a pub_ipv4-nek!")
        if Host.objects.exclude(id=self.id).filter(pub_ipv4=self.ipv4):
            raise ValidationError("Egy masik host natolt cimet nem hasznalhatod sajat ipv4-nek")
        self.full_clean()
        super(Host, self).save(*args, **kwargs)

    def enable_net(self):
        self.groups.add(Group.objects.get(name="netezhet"))

    def add_port(self, proto, public, private):
        proto = "tcp" if (proto == "tcp") else "udp"
        if public < 1024:
            raise ValidationError("Csak az 1024 feletti portok hasznalhatok")
        for host in Host.objects.filter(pub_ipv4=self.pub_ipv4):
            if host.rules.filter(nat=True, proto=proto, dport=public):
                raise ValidationError("A %s %s port mar hasznalva" % (proto, public))
        rule = Rule(direction='1', owner=self.owner, dport=public, proto=proto, nat=True, accept=True, r_type="host", nat_dport=private, host=host, foreign_network=VlanGroup.objects.get(name=settings["default_vlangroup"]))
        rule.full_clean()
        rule.save()

    def del_port(self, proto, public):
        self.rules.filter(owner=self.owner, proto=proto, nat=True, dport=public).delete()

    def list_ports(self):
        retval = []
        for rule in self.rules.filter(owner=self.owner, nat=True):
            retval.append({'proto': rule.proto, 'public': rule.dport, 'private': rule.nat_dport})
        return retval

    def del_rules(self):
        self.rules.filter(owner=self.owner).delete()

class Firewall(models.Model):
    name = models.CharField(max_length=20, unique=True)

    def __unicode__(self):
        return self.name

