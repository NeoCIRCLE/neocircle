from django.contrib.auth.models import User
from django.db import models
from django.forms import fields
from django.utils.translation import ugettext_lazy as _
from firewall.fields import *
from south.modelsinspector import add_introspection_rules

class Rule(models.Model):
     CHOICES = (('host', 'host'), ('firewall', 'firewall'), ('vlan', 'vlan'))
     direction = models.BooleanField()
     description = models.TextField(blank=True)
     vlan = models.ManyToManyField('Vlan', symmetrical=False, blank=True, null=True)
     extra = models.TextField(blank=True);
     action = models.BooleanField(default=False)
     owner = models.ForeignKey(User, blank=True, null=True)
     r_type = models.CharField(max_length=10, choices=CHOICES)
     nat = models.BooleanField(default=False)
     nat_dport = models.IntegerField();
     def __unicode__(self):
        return self.desc()
     def desc(self):
	return '[' + self.r_type + '] ' + (self.vlan_l() + '->' + self.r_type if self.direction else self.r_type + '->' + self.vlan_l()) + ' ' + self.description
     def vlan_l(self):
	retval = []
	for vl in self.vlan.all():
		retval.append(vl.name)
	return ', '.join(retval)

class Vlan(models.Model):
    vid = models.IntegerField(unique=True)
    name = models.CharField(max_length=20, unique=True, validators=[val_alfanum])
    prefix4 = models.IntegerField(default=16);
    prefix6 = models.IntegerField(default=80);
    interface = models.CharField(max_length=20, unique=True)
    net4 = models.GenericIPAddressField(protocol='ipv4', unique=True)
    net6 = models.GenericIPAddressField(protocol='ipv6', unique=True)
    ipv4 = models.GenericIPAddressField(protocol='ipv4', unique=True)
    ipv6 = models.GenericIPAddressField(protocol='ipv6', unique=True)
    snat_ip = models.GenericIPAddressField(protocol='ipv4', blank=True, null=True)
    snat_to = models.ManyToManyField('self', symmetrical=False, blank=True, null=True)
    rules = models.ManyToManyField('Rule', related_name="%(app_label)s_%(class)s_related", symmetrical=False, blank=True, null=True)
    description = models.TextField(blank=True)
    comment = models.TextField(blank=True)
    domain = models.TextField(blank=True, validators=[val_domain])
    dhcp_pool = models.TextField(blank=True)
    def __unicode__(self):
        return self.name
    def net_ipv6(self):
	return self.net6 + "/" + str(self.prefix6)
    def net_ipv4(self):
	return self.net4 + "/" + str(self.prefix4)
    def rules_l(self):
	retval = []
	for rl in self.rules.all():
		retval.append(str(rl))
	return ', '.join(retval)
    def snat_to_l(self):
	retval = []
	for rl in self.snat_to.all():
		retval.append(str(rl))
	return ', '.join(retval)

class Group(models.Model):
    name = models.CharField(max_length=20, unique=True)
    rules = models.ManyToManyField('Rule', symmetrical=False, blank=True, null=True)
    def __unicode__(self):
        return self.name

class Host(models.Model):
    hostname = models.CharField(max_length=20, unique=True, validators=[val_alfanum])
    mac = MACAddressField(unique=True)
    ipv4 = models.GenericIPAddressField(protocol='ipv4', unique=True)
    pub_ipv4 = models.GenericIPAddressField(protocol='ipv4', unique=True, blank=True, null=True)
    ipv6 = models.GenericIPAddressField(protocol='ipv6', unique=True, blank=True)
    description = models.TextField(blank=True)
    comment = models.TextField(blank=True)
    location = models.TextField(blank=True)
    vlan = models.ForeignKey('Vlan')
    owner = models.ForeignKey(User)
    groups = models.ManyToManyField('Group', symmetrical=False, blank=True, null=True)
    rules = models.ManyToManyField('Rule', symmetrical=False, blank=True, null=True)
    def __unicode__(self):
        return self.hostname
    def save(self, *args, **kwargs):
        if not self.id and not self.ipv6:
            self.ipv6 = ipv4_2_ipv6(self.ipv4)
        super(Host, self).save(*args, **kwargs)
    def groups_l(self):
	retval = []
	for grp in self.groups.all():
		retval.append(grp.name)
	return ', '.join(retval)
    def rules_l(self):
	retval = []
	for rl in self.rules.all():
		retval.append(str(rl))
	return ', '.join(retval)
		

class Firewall(models.Model):
    name = models.CharField(max_length=20, unique=True)
    rules = models.ManyToManyField('Rule', symmetrical=False, blank=True, null=True)
    def __unicode__(self):
        return self.name

