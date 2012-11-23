from django.forms import fields
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from south.modelsinspector import add_introspection_rules
import re

mac_re = re.compile(r'^([0-9a-fA-F]{2}([:-]?|$)){6}$')
alfanum_re = re.compile(r'^[A-Za-z0-9_-]+$')
domain_re = re.compile(r'^([A-Za-z0-9_-]\.?)+$')

class MACAddressFormField(fields.RegexField):
    default_error_messages = {
        'invalid': _(u'Enter a valid MAC address.'),
    }

    def __init__(self, *args, **kwargs):
        super(MACAddressFormField, self).__init__(mac_re, *args, **kwargs)

class MACAddressField(models.Field):
    empty_strings_allowed = False
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 17
        super(MACAddressField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return "CharField"

    def formfield(self, **kwargs):
        defaults = {'form_class': MACAddressFormField}
        defaults.update(kwargs)
        return super(MACAddressField, self).formfield(**defaults)
add_introspection_rules([], ["^firewall\.models\.MACAddressField"])

def val_alfanum(value):
     if not alfanum_re.search(value):
          raise ValidationError(u'%s - csak betut, kotojelet, alahuzast, szamot tartalmazhat!' % value)

def val_domain(value):
     if not domain_re.search(value):
          raise ValidationError(u'%s - helytelen domain' % value)


class Rule(models.Model):
#     DIRECTION_CH=(('TOHOST', 1), ('FROMHOST', 0))
     direction = models.BooleanField()
     description = models.TextField(blank=True)
     vlan = models.ForeignKey('Vlan')
     extra = models.TextField(blank=True);
     action = models.BooleanField(default=False)
#     owner = models.ForeignKey(User)
     def __unicode__(self):
        return self.description

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
    en_dst = models.ManyToManyField('self', symmetrical=False, blank=True, null=True)
    description = models.TextField(blank=True)
    comment = models.TextField(blank=True)
    domain = models.TextField(blank=True, validators=[val_domain])
    dhcp_pool = models.TextField(blank=True)
    def __unicode__(self):
        return self.name
    def en_dst_vlan(self):
        return self.en_dst.all()
    def net_ipv6(self):
	return self.net6 + "/" + str(self.prefix6)
    def net_ipv4(self):
	return self.net4 + "/" + str(self.prefix4)

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
    ipv6 = models.GenericIPAddressField(protocol='ipv6', unique=True)
    description = models.TextField(blank=True)
    comment = models.TextField(blank=True)
    location = models.TextField(blank=True)
    vlan = models.ForeignKey('Vlan')
    owner = models.ForeignKey(User)
    groups = models.ManyToManyField('Group', symmetrical=False, blank=True, null=True)
    rules = models.ManyToManyField('Rule', symmetrical=False, blank=True, null=True)
    def __unicode__(self):
        return self.hostname
    def groups_l(self):
	retval = []
	for grp in self.groups.all():
		retval.append(grp.name)
	return ', '.join(retval)
    def rules_l(self):
	retval = []
	for rl in self.rules.all():
		retval.append(rl.description)
	return ', '.join(retval)
		

class Firewall(models.Model):
    name = models.CharField(max_length=20, unique=True)
    rules = models.ManyToManyField('Rule', symmetrical=False, blank=True, null=True)
    def __unicode__(self):
        return self.name

