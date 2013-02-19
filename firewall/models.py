# -*- coding: utf8 -*-

from django.contrib.auth.models import User
from django.db import models
from django.forms import fields, ValidationError
from django.utils.translation import ugettext_lazy as _
from firewall.fields import *
from south.modelsinspector import add_introspection_rules
from django.core.validators import MinValueValidator, MaxValueValidator
from cloud.settings import firewall_settings as settings
from django.utils.ipv6 import is_valid_ipv6_address
from django.db.models.signals import post_save
import re

class Rule(models.Model):
    CHOICES_type = (('host', 'host'), ('firewall', 'firewall'),
            ('vlan', 'vlan'))
    CHOICES_proto = (('tcp', 'tcp'), ('udp', 'udp'), ('icmp', 'icmp'))
    CHOICES_dir = (('0', 'out'), ('1', 'in'))

    direction = models.CharField(max_length=1, choices=CHOICES_dir,
            blank=False)
    description = models.TextField(blank=True)
    foreign_network = models.ForeignKey('VlanGroup',
            related_name="ForeignRules")
    dport = models.IntegerField(blank=True, null=True,
            validators=[MinValueValidator(1), MaxValueValidator(65535)])
    sport = models.IntegerField(blank=True, null=True,
            validators=[MinValueValidator(1), MaxValueValidator(65535)])
    proto = models.CharField(max_length=10, choices=CHOICES_proto,
            blank=True, null=True)
    extra = models.TextField(blank=True)
    accept = models.BooleanField(default=False)
    owner = models.ForeignKey(User, blank=True, null=True)
    r_type = models.CharField(max_length=10, choices=CHOICES_type)
    nat = models.BooleanField(default=False)
    nat_dport = models.IntegerField(blank=True, null=True,
            validators=[MinValueValidator(1), MaxValueValidator(65535)])
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    vlan = models.ForeignKey('Vlan', related_name="rules", blank=True,
            null=True)
    vlangroup = models.ForeignKey('VlanGroup', related_name="rules",
            blank=True, null=True)
    host = models.ForeignKey('Host', related_name="rules", blank=True,
            null=True)
    hostgroup = models.ForeignKey('Group', related_name="rules",
            blank=True, null=True)
    firewall = models.ForeignKey('Firewall', related_name="rules",
            blank=True, null=True)

    def __unicode__(self):
        return self.desc()

    def clean(self):
        count = 0
        for field in [self.vlan, self.vlangroup, self.host, self.hostgroup,
                self.firewall]:
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
        return (u'[' + self.r_type + u'] ' +
                (unicode(self.foreign_network) + u' ▸ ' + self.r_type
                    if self.direction == '1' else self.r_type + u' ▸ ' +
                    unicode(self.foreign_network)) + u' ' + para + u' ' +
                self.description)

class Vlan(models.Model):
    vid = models.IntegerField(unique=True)
    name = models.CharField(max_length=20, unique=True,
            validators=[val_alfanum])
    prefix4 = models.IntegerField(default=16)
    prefix6 = models.IntegerField(default=80)
    interface = models.CharField(max_length=20, unique=True)
    net4 = models.GenericIPAddressField(protocol='ipv4', unique=True)
    net6 = models.GenericIPAddressField(protocol='ipv6', unique=True)
    ipv4 = models.GenericIPAddressField(protocol='ipv4', unique=True)
    ipv6 = models.GenericIPAddressField(protocol='ipv6', unique=True)
    snat_ip = models.GenericIPAddressField(protocol='ipv4', blank=True,
            null=True)
    snat_to = models.ManyToManyField('self', symmetrical=False, blank=True,
            null=True)
    description = models.TextField(blank=True)
    comment = models.TextField(blank=True)
    domain = models.ForeignKey('Domain')
    reverse_domain = models.TextField(validators=[val_reverse_domain])
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
    vlans = models.ManyToManyField('Vlan', symmetrical=False, blank=True,
            null=True)
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

class Host(models.Model):
    hostname = models.CharField(max_length=40, unique=True,
            validators=[val_alfanum])
    reverse = models.CharField(max_length=40, validators=[val_domain],
            blank=True, null=True)
    mac = MACAddressField(unique=True)
    ipv4 = models.GenericIPAddressField(protocol='ipv4', unique=True)
    pub_ipv4 = models.GenericIPAddressField(protocol='ipv4', blank=True,
            null=True)
    ipv6 = models.GenericIPAddressField(protocol='ipv6', unique=True,
            blank=True, null=True)
    shared_ip = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    comment = models.TextField(blank=True)
    location = models.TextField(blank=True)
    vlan = models.ForeignKey('Vlan')
    owner = models.ForeignKey(User)
    groups = models.ManyToManyField('Group', symmetrical=False, blank=True,
            null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.hostname

    def save(self, *args, **kwargs):
        id = self.id
        if not self.id and self.ipv6 == "auto":
            self.ipv6 = ipv4_2_ipv6(self.ipv4)
        if (not self.shared_ip and self.pub_ipv4 and Host.objects.
                exclude(id=self.id).filter(pub_ipv4=self.pub_ipv4)):
            raise ValidationError(_("If shared_ip has been checked, "
                "pub_ipv4 has to be unique."))
        if Host.objects.exclude(id=self.id).filter(pub_ipv4=self.ipv4):
            raise ValidationError(_("You can't use another host's NAT'd "
                "address as your own IPv4."))
        self.full_clean()
        super(Host, self).save(*args, **kwargs)
        if id is None:
            Record(domain=self.vlan.domain, host=self, type='A',
                    owner=self.owner).save()
            if self.ipv6:
                Record(domain=self.vlan.domain, host=self, type='AAAA',
                        owner=self.owner).save()

    def enable_net(self):
        self.groups.add(Group.objects.get(name="netezhet"))

    def add_port(self, proto, public, private):
        proto = "tcp" if (proto == "tcp") else "udp"
        if public < 1024:
            raise ValidationError(_("Only ports above 1024 can be used."))
        for host in Host.objects.filter(pub_ipv4=self.pub_ipv4):
            if host.rules.filter(nat=True, proto=proto, dport=public):
                raise ValidationError(_("Port %s %s is already in use.") %
                        (proto, public))
        rule = Rule(direction='1', owner=self.owner, dport=public,
                proto=proto, nat=True, accept=True, r_type="host",
                nat_dport=private, host=self, foreign_network=VlanGroup.
                    objects.get(name=settings["default_vlangroup"]))
        rule.full_clean()
        rule.save()

    def del_port(self, proto, public):
        self.rules.filter(owner=self.owner, proto=proto, nat=True,
                dport=public).delete()

    def list_ports(self):
        retval = []
        for rule in self.rules.filter(owner=self.owner, nat=True):
            retval.append({'proto': rule.proto, 'public': rule.dport,
                'private': rule.nat_dport})
        return retval

    def del_rules(self):
        self.rules.filter(owner=self.owner).delete()

    def get_fqdn(self):
        return self.hostname + u'.' + unicode(self.vlan.domain)


class Firewall(models.Model):
    name = models.CharField(max_length=20, unique=True)

    def __unicode__(self):
        return self.name

class Domain(models.Model):
    name = models.CharField(max_length=40, validators=[val_domain])
    owner = models.ForeignKey(User)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    ttl = models.IntegerField(default=600)
    description = models.TextField(blank=True)

    def __unicode__(self):
        return self.name

class Record(models.Model):
    CHOICES_type = (('A', 'A'), ('CNAME', 'CNAME'), ('AAAA', 'AAAA'),
            ('MX', 'MX'), ('NS', 'NS'), ('PTR', 'PTR'), ('TXT', 'TXT'))
    name = models.CharField(max_length=40, validators=[val_domain],
            blank=True, null=True)
    domain = models.ForeignKey('Domain')
    host = models.ForeignKey('Host', blank=True, null=True)
    type = models.CharField(max_length=6, choices=CHOICES_type)
    address = models.CharField(max_length=40, blank=True, null=True)
    ttl = models.IntegerField(default=600)
    owner = models.ForeignKey(User)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.desc()

    def desc(self):
        a = self.get_data()
        if a:
            return a['name'] + u' ' + a['type'] + u' ' + a['address']
        return '(empty)'

    def save(self, *args, **kwargs):
        self.full_clean()
        super(Record, self).save(*args, **kwargs)

    def clean(self):
        if self.name and self.name.endswith(u'.'):
            raise ValidationError(_("Domain can't be terminated with a dot."))

        if self.host and self.type in ['CNAME', 'A', 'AAAA']:
            if self.type == 'CNAME':
                if not self.name or self.address:
                    raise ValidationError(_("Only the 'name' field should "
                            "be filled with a CNAME record if a host is "
                            "set."))
            elif self.name or self.address:
                raise ValidationError(_("'name' and 'address' can't be "
                        "specified with an A or AAAA record if a host is "
                        "set."))
        else:
            if not self.address:
                raise ValidationError(_("'address' field must be filled."))

            if self.type == 'A':
                if not ipv4_re.match(self.address):
                    raise ValidationError(_("Not a valid IPv4 address."))
            elif self.type in ['CNAME', 'NS', 'PTR', 'TXT']:
                if not domain_re.match(self.address):
                    raise ValidationError(_("Not a valid domain."))
            elif self.type == 'AAAA':
                if not is_valid_ipv6_address(self.address):
                    raise ValidationError(_("Not a valid IPv6 address."))
            elif self.type == 'MX':
                mx = self.address.split(':', 1)
                if not (len(mx) == 2 and mx[0].isdigit() and
                        domain_re.match(mx[1])):
                    raise ValidationError(_("Invalid address. "
                        "Valid format: <priority>:<hostname>"))
            else:
                raise ValidationError(_("Unknown record."))

    def get_data(self):
        retval = { 'name': self.name, 'type': self.type, 'ttl': self.ttl,
                'address': self.address }
        if self.host and self.type in ['CNAME', 'A', 'AAAA']:
            if self.type == 'A':
                retval['address'] = (self.host.pub_ipv4
                        if self.host.pub_ipv4 and not self.host.shared_ip
                        else self.host.ipv4)
                retval['name'] = self.host.get_fqdn()
            elif self.type == 'AAAA':
                if not self.host.ipv6:
                    return None
                retval['address'] = self.host.ipv6
                retval['name'] = self.host.get_fqdn()
            elif self.type == 'CNAME':
                retval['address'] = self.host.get_fqdn()
                retval['name'] = self.name + u'.' + unicode(self.domain)
        else:
            if not self.name:
                retval['name'] = unicode(self.domain)
            else:
                retval['name'] = self.name + u'.' + unicode(self.domain)
        if not (retval['address'] and retval['name']):
            return None
        return retval

class Blacklist(models.Model):
    CHOICES_type = (('permban', 'permanent ban'), ('tempban', 'temporary ban'), ('whitelist', 'whitelist'))
    ipv4 = models.GenericIPAddressField(protocol='ipv4', unique=True)
    reason = models.TextField(blank=True)
    snort_message = models.TextField(blank=True)
    type = models.CharField(max_length=10, choices=CHOICES_type, default='tempban')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.full_clean()
        super(Blacklist, self).save(*args, **kwargs)
    def __unicode__(self):
        return self.ipv4

def send_task(sender, instance, created, **kwargs):
    from firewall.tasks import ReloadTask
    ReloadTask.apply_async(args=[sender.__name__])


post_save.connect(send_task, sender=Host)
post_save.connect(send_task, sender=Rule)
post_save.connect(send_task, sender=Domain)
post_save.connect(send_task, sender=Record)
post_save.connect(send_task, sender=Vlan)
post_save.connect(send_task, sender=Firewall)
post_save.connect(send_task, sender=Group)
post_save.connect(send_task, sender=Host)
post_save.connect(send_task, sender=Blacklist)
