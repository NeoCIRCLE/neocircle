# -*- coding: utf-8 -*-

# Copyright 2014 Budapest University of Technology and Economics (BME IK)
#
# This file is part of CIRCLE Cloud.
#
# CIRCLE is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# CIRCLE is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along
# with CIRCLE.  If not, see <http://www.gnu.org/licenses/>.

from string import ascii_letters
from itertools import islice, ifilter, chain
from math import ceil
import logging
import random

from django.contrib.auth.models import User
from django.db import models
from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _
from firewall.fields import (MACAddressField, val_alfanum, val_reverse_domain,
                             val_ipv6_template, val_domain, val_ipv4,
                             val_domain_wildcard,
                             val_ipv6, val_mx,
                             IPNetworkField, IPAddressField)
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.urlresolvers import reverse
import django.conf
from django.db.models.signals import post_save, post_delete
from celery.exceptions import TimeoutError
from netaddr import IPSet, EUI, IPNetwork, IPAddress, ipv6_full

from common.models import method_cache, WorkerNotFound, HumanSortField
from firewall.tasks.local_tasks import reloadtask
from firewall.tasks.remote_tasks import get_dhcp_clients
from .iptables import IptRule
from acl.models import AclBase


logger = logging.getLogger(__name__)
settings = django.conf.settings.FIREWALL_SETTINGS


class Rule(models.Model):

    """
    A rule of a packet filter, changing the behavior of a host, vlan or
    firewall.

    Some rules accept or deny packets matching some criteria.
    Others set address translation or other free-form iptables parameters.
    """
    CHOICES_type = (('host', 'host'), ('firewall', 'firewall'),
                    ('vlan', 'vlan'))
    CHOICES_proto = (('tcp', 'tcp'), ('udp', 'udp'), ('icmp', 'icmp'))
    CHOICES_dir = (('out', _('out')), ('in', _('in')))
    CHOICES_action = (('accept', _('accept')), ('drop', _('drop')),
                      ('ignore', _('ignore')))

    direction = models.CharField(max_length=3, choices=CHOICES_dir,
                                 blank=False, verbose_name=_("direction"),
                                 help_text=_("If the rule matches egress "
                                             "or ingress packets."))
    description = models.TextField(blank=True, verbose_name=_('description'),
                                   help_text=_("Why is the rule needed, "
                                               "or how does it work."))
    foreign_network = models.ForeignKey(
        'VlanGroup', verbose_name=_("foreign network"),
        help_text=_("The group of vlans the matching packet goes to "
                    "(direction out) or from (in)."),
        related_name="ForeignRules")
    dport = models.IntegerField(
        blank=True, null=True, verbose_name=_("dest. port"),
        validators=[MinValueValidator(1), MaxValueValidator(65535)],
        help_text=_("Destination port number of packets that match."))
    sport = models.IntegerField(
        blank=True, null=True, verbose_name=_("source port"),
        validators=[MinValueValidator(1), MaxValueValidator(65535)],
        help_text=_("Source port number of packets that match."))
    weight = models.IntegerField(
        verbose_name=_("weight"),
        validators=[MinValueValidator(1), MaxValueValidator(65535)],
        help_text=_("Rule weight"),
        default=30000)
    proto = models.CharField(max_length=10, choices=CHOICES_proto,
                             blank=True, null=True, verbose_name=_("protocol"),
                             help_text=_("Protocol of packets that match."))
    extra = models.TextField(blank=True, verbose_name=_("extra arguments"),
                             help_text=_("Additional arguments passed "
                                         "literally to the iptables-rule."))
    action = models.CharField(max_length=10, choices=CHOICES_action,
                              default='drop', verbose_name=_('action'),
                              help_text=_("Accept, drop or ignore the "
                                          "matching packets."))
    owner = models.ForeignKey(User, blank=True, null=True,
                              verbose_name=_("owner"),
                              help_text=_("The user responsible for "
                                          "this rule."))

    nat = models.BooleanField(default=False, verbose_name=_("NAT"),
                              help_text=_("If network address translation "
                                          "should be done."))
    nat_external_port = models.IntegerField(
        blank=True, null=True,
        help_text=_("Rewrite destination port number to this if NAT is "
                    "needed."),
        validators=[MinValueValidator(1), MaxValueValidator(65535)])
    nat_external_ipv4 = IPAddressField(
        version=4, blank=True, null=True,
        verbose_name=_('external IPv4 address'))

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("created at"))
    modified_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("modified at"))

    vlan = models.ForeignKey('Vlan', related_name="rules", blank=True,
                             null=True, verbose_name=_("vlan"),
                             help_text=_("Vlan the rule applies to "
                                         "(if type is vlan)."))
    vlangroup = models.ForeignKey('VlanGroup', related_name="rules",
                                  blank=True, null=True, verbose_name=_(
                                      "vlan group"),
                                  help_text=_("Group of vlans the rule "
                                              "applies to (if type is vlan)."))
    host = models.ForeignKey('Host', related_name="rules", blank=True,
                             verbose_name=_('host'), null=True,
                             help_text=_("Host the rule applies to "
                                         "(if type is host)."))
    hostgroup = models.ForeignKey(
        'Group', related_name="rules", verbose_name=_("host group"),
        blank=True, null=True, help_text=_("Group of hosts the rule applies "
                                           "to (if type is host)."))
    firewall = models.ForeignKey(
        'Firewall', related_name="rules", verbose_name=_("firewall"),
                                 help_text=_("Firewall the rule applies to "
                                             "(if type is firewall)."),
        blank=True, null=True)

    def __unicode__(self):
        return self.desc()

    def clean(self):
        fields = [self.vlan, self.vlangroup, self.host, self.hostgroup,
                  self.firewall]
        selected_fields = [field for field in fields if field]
        if len(selected_fields) > 1:
            raise ValidationError(_('Only one field can be selected.'))
        elif len(selected_fields) < 1:
            raise ValidationError(
                _('One of the following fields must be selected: '
                  'vlan, vlan group, host, host group, firewall.'))

    def get_external_ipv4(self):
        return (self.nat_external_ipv4
                if self.nat_external_ipv4 else self.host.get_external_ipv4())

    def get_external_port(self, proto='ipv4'):
        assert proto in ('ipv4', 'ipv6')
        if proto == 'ipv4' and self.nat_external_port:
            return self.nat_external_port
        else:
            return self.dport

    def desc(self):
        """Return a short string representation of the current rule.
        """
        return u'[%(type)s] %(src)s ▸ %(dst)s %(para)s %(desc)s' % {
            'type': self.r_type,
            'src': (unicode(self.foreign_network) if self.direction == 'in'
                    else self.r_type),
            'dst': (self.r_type if self.direction == 'out'
                    else unicode(self.foreign_network)),
            'para': ((("proto=%s " % self.proto) if self.proto else '') +
                     (("sport=%s " % self.sport) if self.sport else '') +
                     (("dport=%s " % self.dport) if self.dport else '')),
            'desc': self.description}

    @property
    def r_type(self):
        fields = [self.vlan, self.vlangroup, self.host, self.hostgroup,
                  self.firewall]
        for field in fields:
            if field is not None:
                return field.__class__.__name__.lower()
        return None

    def get_absolute_url(self):
        return reverse('network.rule', kwargs={'pk': self.pk})

    def get_chain_name(self, local, remote):
        if local:  # host or vlan
            if self.direction == 'in':
                # remote -> local
                return '%s_%s' % (remote.name, local.name)
            else:
                # local -> remote
                return '%s_%s' % (local.name, remote.name)
            # firewall rule
        elif self.firewall_id:
            return 'INPUT' if self.direction == 'in' else 'OUTPUT'

    def get_ipt_rules(self, host=None):
        # action
        action = 'LOG_ACC' if self.action == 'accept' else 'LOG_DROP'

        # 'chain_name': rule dict
        retval = {}

        # src and dst addresses
        src = None
        dst = None

        if host:
            ip = (host.ipv4, host.ipv6_with_host_prefixlen)
            if self.direction == 'in':
                dst = ip
            else:
                src = ip
            vlan = host.vlan
        elif self.vlan_id:
            vlan = self.vlan
        else:
            vlan = None

        if vlan and not vlan.managed:
            return retval

        # process foreign vlans
        for foreign_vlan in self.foreign_network.vlans.all():
            if not foreign_vlan.managed:
                continue

            r = IptRule(priority=self.weight, action=action,
                        proto=self.proto, extra=self.extra,
                        comment='Rule #%s' % self.pk,
                        src=src, dst=dst, dport=self.dport, sport=self.sport)
            chain_name = self.get_chain_name(local=vlan, remote=foreign_vlan)
            retval[chain_name] = r

        return retval

    @classmethod
    def portforwards(cls, host=None):
        qs = cls.objects.filter(dport__isnull=False, direction='in')
        if host is not None:
            qs = qs.filter(host=host)
        return qs

    class Meta:
        app_label = 'firewall'
        verbose_name = _("rule")
        verbose_name_plural = _("rules")
        ordering = (
            'direction',
            'proto',
            'sport',
            'dport',
            'nat_external_port',
            'host',
        )


class Vlan(AclBase, models.Model):

    """
    A vlan of the network,

    Networks controlled by this framework are split into separated subnets.
    These networks are izolated by the vlan (virtual lan) technology, which is
    commonly used by managed network switches to partition the network.

    Each vlan network has a unique identifier, a name, a unique IPv4 and IPv6
    range. The gateway also has an IP address in each range.
    """

    ACL_LEVELS = (
        ('user', _('user')),
        ('operator', _('operator')),
    )
    CHOICES_NETWORK_TYPE = (('public', _('public')),
                            ('portforward', _('portforward')))
    vid = models.IntegerField(unique=True,
                              verbose_name=_('VID'),
                              help_text=_('The vlan ID of the subnet.'),
                              validators=[MinValueValidator(1),
                                          MaxValueValidator(4095)])
    name = models.CharField(max_length=20,
                            unique=True,
                            verbose_name=_('Name'),
                            help_text=_('The short name of the subnet.'),
                            validators=[val_alfanum])
    network4 = IPNetworkField(unique=False,
                              version=4,
                              verbose_name=_('IPv4 address/prefix'),
                              help_text=_(
                                  'The IPv4 address and the prefix length '
                                  'of the gateway. '
                                  'Recommended value is the last '
                                  'valid address of the subnet, '
                                  'for example '
                                  '10.4.255.254/16 for 10.4.0.0/16.'))
    host_ipv6_prefixlen = models.IntegerField(
        verbose_name=_('IPv6 prefixlen/host'),
        help_text=_('The prefix length of the subnet assigned to a host. '
                    'For example /112 = 65536 addresses/host.'),
        default=112,
        validators=[MinValueValidator(1), MaxValueValidator(128)])
    network6 = IPNetworkField(unique=False,
                              version=6,
                              null=True,
                              blank=True,
                              verbose_name=_('IPv6 address/prefix'),
                              help_text=_(
                                  'The IPv6 address and the prefix length '
                                  'of the gateway.'))
    snat_ip = models.GenericIPAddressField(protocol='ipv4', blank=True,
                                           null=True,
                                           verbose_name=_('NAT IP address'),
                                           help_text=_(
                                               'Common IPv4 address used for '
                                               'address translation of '
                                               'connections to the networks '
                                               'selected below '
                                               '(typically to the internet).'))
    snat_to = models.ManyToManyField('self', symmetrical=False, blank=True,
                                     verbose_name=_('NAT to'),
                                     help_text=_(
                                         'Connections to these networks '
                                         'should be network address '
                                         'translated, i.e. their source '
                                         'address is rewritten to the value '
                                         'of NAT IP address.'))
    network_type = models.CharField(choices=CHOICES_NETWORK_TYPE,
                                    verbose_name=_('network type'),
                                    default='portforward',
                                    max_length=20)
    managed = models.BooleanField(default=True, verbose_name=_('managed'))
    description = models.TextField(blank=True, verbose_name=_('description'),
                                   help_text=_(
                                       'Description of the goals and elements '
                                       'of the vlan network.'))
    comment = models.TextField(blank=True, verbose_name=_('comment'),
                               help_text=_(
                                   'Notes, comments about the network'))
    domain = models.ForeignKey('Domain', verbose_name=_('domain name'),
                               help_text=_('Domain name of the members of '
                                           'this network.'))
    reverse_domain = models.TextField(
        validators=[val_reverse_domain],
        verbose_name=_('reverse domain'),
        help_text=_('Template of the IPv4 reverse domain name that '
                    'should be generated for each host. The template '
                    'should contain four tokens: "%(a)d", "%(b)d", '
                    '"%(c)d", and "%(d)d", representing the four bytes '
                    'of the address, respectively, in decimal notation. '
                    'For example, the template for the standard reverse '
                    'address is: "%(d)d.%(c)d.%(b)d.%(a)d.in-addr.arpa".'),
        default="%(d)d.%(c)d.%(b)d.%(a)d.in-addr.arpa")
    ipv6_template = models.TextField(
        blank=True,
        help_text=_('Template for translating IPv4 addresses to IPv6. '
                    'Automatically generated hosts in dual-stack networks '
                    'will get this address. The template '
                    'can contain four tokens: "%(a)d", "%(b)d", '
                    '"%(c)d", and "%(d)d", representing the four bytes '
                    'of the IPv4 address, respectively, in decimal notation. '
                    'Moreover you can use any standard printf format '
                    'specification like %(a)02x to get the first byte as two '
                    'hexadecimal digits. Usual choices for mapping '
                    '198.51.100.0/24 to 2001:0DB8:1:1::/64 would be '
                    '"2001:db8:1:1:%(d)d::" and "2001:db8:1:1:%(d)02x00::".'),
        validators=[val_ipv6_template], verbose_name=_('ipv6 template'))
    dhcp_pool = models.TextField(blank=True, verbose_name=_('DHCP pool'),
                                 help_text=_(
                                     'The address range of the DHCP pool: '
                                     'empty for no DHCP service, "manual" for '
                                     'no DHCP pool, or the first and last '
                                     'address of the range separated by a '
                                     'space.'))
    created_at = models.DateTimeField(auto_now_add=True,
                                      verbose_name=_('created at'))
    owner = models.ForeignKey(User, blank=True, null=True,
                              verbose_name=_('owner'))
    modified_at = models.DateTimeField(auto_now=True,
                                       verbose_name=_('modified at'))

    class Meta:
        app_label = 'firewall'
        verbose_name = _("vlan")
        verbose_name_plural = _("vlans")
        ordering = ('vid', )

    def clean(self):
        super(Vlan, self).clean()
        if self.ipv6_template:
            if not self.network6:
                raise ValidationError(
                    _("You cannot specify an IPv6 template if there is no "
                      "IPv6 network set."))
            for i in (self.network4[1], self.network4[-1]):
                i6 = self.convert_ipv4_to_ipv6(i)
                if i6 not in self.network6:
                    raise ValidationError(
                        _("%(ip6)s (translated from %(ip4)s) is outside of "
                          "the IPv6 network.") % {"ip4": i, "ip6": i6})
        if self.network6:
            tpl, prefixlen = self._magic_ipv6_template(self.network4,
                                                       self.network6)
            if not self.ipv6_template:
                self.ipv6_template = tpl
            if not self.host_ipv6_prefixlen:
                self.host_ipv6_prefixlen = prefixlen

    @staticmethod
    def _host_bytes(prefixlen, maxbytes):
        return int(ceil((maxbytes - prefixlen / 8.0)))

    @staticmethod
    def _append_hexa(s, v, lasthalf):
        if lasthalf:  # can use last half word
            assert s[-1] == "0" or s[-1].endswith("00")
            if s[-1].endswith("00"):
                s[-1] = s[-1][:-2]
            s[-1] += "%({})02x".format(v)
            s[-1].lstrip("0")
        else:
            s.append("%({})02x00".format(v))

    @classmethod
    def _magic_ipv6_template(cls, network4, network6, verbose=None):
        """Offer a sensible ipv6_template value.

        Based on prefix lengths the method magically selects verbose (decimal)
        format:
        >>> Vlan._magic_ipv6_template(IPNetwork("198.51.100.0/24"),
        ...                           IPNetwork("2001:0DB8:1:1::/64"))
        ('2001:db8:1:1:%(d)d::', 80)

        However you can explicitly select non-verbose, i.e. hexa format:
        >>> Vlan._magic_ipv6_template(IPNetwork("198.51.100.0/24"),
        ...                           IPNetwork("2001:0DB8:1:1::/64"), False)
        ('2001:db8:1:1:%(d)02x00::', 72)
        """
        host4_bytes = cls._host_bytes(network4.prefixlen, 4)
        host6_bytes = cls._host_bytes(network6.prefixlen, 16)
        if host4_bytes > host6_bytes:
            raise ValidationError(
                _("IPv6 network is too small to map IPv4 addresses to it."))
        letters = ascii_letters[4-host4_bytes:4]
        remove = host6_bytes // 2
        ipstr = network6.network.format(ipv6_full)
        s = ipstr.split(":")[0:-remove]
        if verbose is None:  # use verbose format if net6 much wider
            verbose = 2 * (host4_bytes + 1) < host6_bytes
        if verbose:
            for i in letters:
                s.append("%({})d".format(i))
        else:
            remain = host6_bytes
            for i in letters:
                cls._append_hexa(s, i, remain % 2 == 1)
                remain -= 1
        if host6_bytes > host4_bytes:
            s.append(":")
        tpl = ":".join(s)
        # compute prefix length
        mask = int(IPAddress(tpl % {"a": 1, "b": 1, "c": 1, "d": 1}))
        prefixlen = 128
        while mask % 2 == 0:
            mask /= 2
            prefixlen -= 1
        return (tpl, prefixlen)

    def __unicode__(self):
        return "%s - %s" % ("managed" if self.managed else "unmanaged",
                            self.name)

    def get_absolute_url(self):
        return reverse('network.vlan', kwargs={'vid': self.vid})

    def get_random_addresses(self, used_v4, buffer_size=100, max_hosts=10000):
        addresses = islice(self.network4.iter_hosts(), max_hosts)
        unused_addresses = list(islice(
            ifilter(lambda x: x not in used_v4, addresses), buffer_size))
        random.shuffle(unused_addresses)
        return unused_addresses

    def get_new_address(self):
        hosts = self.host_set
        used_ext_addrs = Host.objects.filter(
            external_ipv4__isnull=False).values_list(
            'external_ipv4', flat=True)
        used_v4 = IPSet(hosts.values_list('ipv4', flat=True)).union(
            used_ext_addrs).union([self.network4.ip])
        used_v6 = IPSet(hosts.exclude(ipv6__isnull=True)
                        .values_list('ipv6', flat=True))

        for ipv4 in self.get_random_addresses(used_v4):
            logger.debug("Found unused IPv4 address %s.", ipv4)
            ipv6 = None
            if self.network6 is not None:
                ipv6 = self.convert_ipv4_to_ipv6(ipv4)
                if ipv6 in used_v6:
                    continue
                else:
                    logger.debug("Found unused IPv6 address %s.", ipv6)
            return {'ipv4': ipv4, 'ipv6': ipv6}
        else:
            raise ValidationError(_("All IP addresses are already in use."))

    def convert_ipv4_to_ipv6(self, ipv4):
        """Convert IPv4 address string to IPv6 address string."""
        if isinstance(ipv4, basestring):
            ipv4 = IPAddress(ipv4, 4)
        nums = {ascii_letters[i]: int(ipv4.words[i]) for i in range(4)}
        return IPAddress(self.ipv6_template % nums)

    def get_dhcp_clients(self):
        macs = set(i.mac for i in self.host_set.all())
        return [{"mac": k, "ip": v["ip"], "hostname": v["hostname"]}
                for k, v in chain(*(fw.get_dhcp_clients().iteritems()
                                    for fw in Firewall.objects.all() if fw))
                if v["interface"] == self.name and EUI(k) not in macs]


class VlanGroup(models.Model):
    """
    A group of Vlans.
    """

    name = models.CharField(max_length=20, unique=True, verbose_name=_('name'),
                            help_text=_('The name of the group.'))
    vlans = models.ManyToManyField('Vlan', symmetrical=False, blank=True,
                                   verbose_name=_('vlans'),
                                   help_text=_('The vlans which are members '
                                               'of the group.'))
    description = models.TextField(blank=True, verbose_name=_('description'),
                                   help_text=_('Description of the group.'))
    owner = models.ForeignKey(User, blank=True, null=True,
                              verbose_name=_('owner'))
    created_at = models.DateTimeField(auto_now_add=True,
                                      verbose_name=_('created at'))
    modified_at = models.DateTimeField(auto_now=True,
                                       verbose_name=_('modified at'))

    class Meta:
        app_label = 'firewall'
        verbose_name = _("vlan group")
        verbose_name_plural = _("vlan groups")
        ordering = ('id', )

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('network.vlan_group', kwargs={'pk': self.pk})


class Group(models.Model):
    """
    A group of hosts.
    """
    name = models.CharField(max_length=20, unique=True, verbose_name=_('name'),
                            help_text=_('The name of the group.'))
    description = models.TextField(blank=True, verbose_name=_('description'),
                                   help_text=_('Description of the group.'))
    owner = models.ForeignKey(User, blank=True, null=True,
                              verbose_name=_('owner'))
    created_at = models.DateTimeField(auto_now_add=True,
                                      verbose_name=_('created at'))
    modified_at = models.DateTimeField(auto_now=True,
                                       verbose_name=_('modified at'))

    class Meta:
        app_label = 'firewall'
        verbose_name = _("host group")
        verbose_name_plural = _("host groups")
        ordering = ('id', )

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('network.group', kwargs={'pk': self.pk})


class Host(models.Model):
    """
    A host of the network.
    """

    hostname = models.CharField(max_length=40,
                                verbose_name=_('hostname'),
                                help_text=_('The alphanumeric hostname of '
                                            'the host, the first part of '
                                            'the FQDN.'),
                                validators=[val_alfanum])
    normalized_hostname = HumanSortField(monitor='hostname', max_length=80)
    reverse = models.CharField(max_length=40, validators=[val_domain],
                               verbose_name=_('reverse'),
                               help_text=_('The fully qualified reverse '
                                           'hostname of the host, if '
                                           'different than hostname.domain.'),
                               blank=True, null=True)
    mac = MACAddressField(unique=True, verbose_name=_('MAC address'),
                          help_text=_('The MAC (Ethernet) address of the '
                                      'network interface. For example: '
                                      '99:AA:BB:CC:DD:EE.'))
    ipv4 = IPAddressField(version=4, unique=True,
                          verbose_name=_('IPv4 address'),
                          help_text=_('The real IPv4 address of the '
                                      'host, for example 10.5.1.34.'))
    external_ipv4 = IPAddressField(
        version=4, blank=True, null=True,
        verbose_name=_('WAN IPv4 address'),
        help_text=_('The public IPv4 address of the host on the wide '
                    'area network, if different.'))
    ipv6 = IPAddressField(version=6, unique=True,
                          blank=True, null=True,
                          verbose_name=_('IPv6 address'),
                          help_text=_('The global IPv6 address of the host'
                                      ', for example 2001:db:88:200::10.'))
    shared_ip = models.BooleanField(default=False, verbose_name=_('shared IP'),
                                    help_text=_(
                                        'If the given WAN IPv4 address is '
                                        'used by multiple hosts.'))
    description = models.TextField(blank=True, verbose_name=_('description'),
                                   help_text=_('What is this host for, what '
                                               'kind of machine is it.'))
    comment = models.TextField(blank=True,
                               verbose_name=_('Notes'))
    location = models.TextField(blank=True, verbose_name=_('location'),
                                help_text=_(
                                    'The physical location of the machine.'))
    vlan = models.ForeignKey('Vlan', verbose_name=_('vlan'),
                             help_text=_(
                                 'Vlan network that the host is part of.'))
    owner = models.ForeignKey(User, verbose_name=_('owner'),
                              help_text=_(
                                  'The person responsible for this host.'))
    groups = models.ManyToManyField('Group', symmetrical=False, blank=True,
                                    verbose_name=_('groups'),
                                    help_text=_(
                                        'Host groups the machine is part of.'))
    created_at = models.DateTimeField(auto_now_add=True,
                                      verbose_name=_('created at'))
    modified_at = models.DateTimeField(auto_now=True,
                                       verbose_name=_('modified at'))

    class Meta(object):
        app_label = 'firewall'
        unique_together = ('hostname', 'vlan')
        ordering = ('normalized_hostname', 'vlan')

    def __unicode__(self):
        return self.hostname

    @property
    def incoming_rules(self):
        return self.rules.filter(direction='in')

    @staticmethod
    def create_ipnetwork(ip, prefixlen):
        try:
            net = IPNetwork(ip)
            net.prefixlen = prefixlen
        except TypeError:
            return None
        else:
            return net

    @property
    def ipv4_with_vlan_prefixlen(self):
        return Host.create_ipnetwork(
            self.ipv4, self.vlan.network4.prefixlen)

    @property
    def ipv6_with_vlan_prefixlen(self):
        return Host.create_ipnetwork(
            self.ipv6, self.vlan.network6.prefixlen)

    @property
    def ipv6_with_host_prefixlen(self):
        return Host.create_ipnetwork(
            self.ipv6, self.vlan.host_ipv6_prefixlen)

    def get_external_ipv4(self):
        return self.external_ipv4 if self.external_ipv4 else self.ipv4

    @property
    def behind_nat(self):
        return self.vlan.network_type != 'public'

    def clean(self):
        if (self.external_ipv4 and not self.shared_ip and self.behind_nat and
                Host.objects.exclude(id=self.id).filter(
                    external_ipv4=self.external_ipv4)):
            raise ValidationError(_("If shared_ip has been checked, "
                                    "external_ipv4 has to be unique."))
        if Host.objects.exclude(id=self.id).filter(external_ipv4=self.ipv4):
            raise ValidationError(_("You can't use another host's NAT'd "
                                    "address as your own IPv4."))

    def save(self, *args, **kwargs):
        if not self.id and self.ipv6 == "auto":
            self.ipv6 = self.vlan.convert_ipv4_to_ipv6(self.ipv4)
        self.full_clean()

        super(Host, self).save(*args, **kwargs)

        # IPv4
        if self.ipv4 is not None:
            if not self.shared_ip and self.external_ipv4:  # DMZ
                ipv4 = self.external_ipv4
            else:
                ipv4 = self.ipv4
            # update existing records
            affected_records = Record.objects.filter(
                host=self, name=self.hostname,
                type='A').update(address=ipv4)
            # create new record
            if affected_records == 0:
                Record(host=self,
                       name=self.hostname,
                       domain=self.vlan.domain,
                       address=self.ipv4,
                       owner=self.owner,
                       description='created by host.save()',
                       type='A').save()

        # IPv6
        if self.ipv6 is not None:
            # update existing records
            affected_records = Record.objects.filter(
                host=self, name=self.hostname,
                type='AAAA').update(address=self.ipv6)
            # create new record
            if affected_records == 0:
                Record(host=self,
                       name=self.hostname,
                       domain=self.vlan.domain,
                       address=self.ipv6,
                       owner=self.owner,
                       description='created by host.save()',
                       type='AAAA').save()

    def get_network_config(self):
        interface = {'addresses': []}

        if self.ipv4 and self.vlan.network4:
            interface['addresses'].append(str(self.ipv4_with_vlan_prefixlen))
            interface['gw4'] = str(self.vlan.network4.ip)

        if self.ipv6 and self.vlan.network6:
            interface['addresses'].append(str(self.ipv6_with_vlan_prefixlen))
            interface['gw6'] = str(self.vlan.network6.ip)

        return interface

    def enable_net(self):
        for i in settings.get('default_host_groups', []):
            self.groups.add(Group.objects.get(name=i))

    def _get_ports_used(self, proto):
        """
        Gives a list of port numbers used for the public IP address of current
        host for the given protocol.

        :param proto: The transport protocol of the generated port (tcp|udp).
        :type proto: str.
        :returns: list -- list of int port numbers used.
        """
        if self.behind_nat:
            ports = Rule.objects.filter(
                host__external_ipv4=self.external_ipv4,
                nat=True,
                proto=proto).values_list('nat_external_port', flat=True)
        else:
            ports = self.rules.filter(proto=proto).values_list(
                'dport', flat=True)
        return set(ports)

    def _get_random_port(self, proto, used_ports=None):
        """
        Get a random unused port for given protocol for current host's public
        IP address.

        :param proto: The transport protocol of the generated port (tcp|udp).
        :type proto: str.
        :param used_ports: Optional set of used ports returned by
                           _get_ports_used.
        :returns: int -- the generated port number.
        :raises: ValidationError
        """
        if used_ports is None:
            used_ports = self._get_ports_used(proto)

        public = random.randint(1024, 21000)  # pick a random port
        if public in used_ports:  # if it's in use, select smallest free one
            for i in range(1024, 21000) + range(24000, 65535):
                if i not in used_ports:
                    public = i
                    break
            else:
                raise ValidationError(
                    _("All %s ports are already in use.") % proto)
        return public

    def add_port(self, proto, public=None, private=None):
        """
        Allow inbound traffic to a port.

        If the host uses a shared IP address, also set up port forwarding.

        :param proto: The transport protocol (tcp|udp).
        :type proto: str.
        :param public: Preferred public port number for forwarding (optional).
        :param private: Port number of host in subject.
        """
        assert proto in ('tcp', 'udp', )
        if public:
            if public in self._get_ports_used(proto):
                raise ValidationError(
                    _("Port %(proto)s %(public)s is already in use.") %
                    {'proto': proto, 'public': public})
        else:
            public = self._get_random_port(proto)

        try:
            vgname = settings["default_vlangroup"]
            vg = VlanGroup.objects.get(name=vgname)
        except VlanGroup.DoesNotExist as e:
            logger.error('Host.add_port: default_vlangroup %s missing. %s',
                         vgname, unicode(e))
        else:
            rule = Rule(direction='in', owner=self.owner, dport=private,
                        proto=proto, nat=False, action='accept',
                        host=self, foreign_network=vg)
            if self.behind_nat:
                rule.nat_external_port = public
                rule.nat = True
            rule.full_clean()
            rule.save()

    def del_port(self, proto, private):
        """
        Remove rules about inbound traffic to a given port.

        If the host uses a shared IP address, also set up port forwarding.

        :param proto: The transport protocol (tcp|udp).
        :type proto: str.
        :param private: Port number of host in subject.
        """

        self.rules.filter(proto=proto, dport=private).delete()

    def get_hostname(self, proto, public=True):
        """
        Get a private or public hostname for host.

        :param proto: The IP version (ipv4|ipv6).
        :type proto: str.
        """
        assert proto in ('ipv6', 'ipv4', )
        if self.reverse:
            return self.reverse
        try:
            if proto == 'ipv6':
                res = self.record_set.filter(type='AAAA',
                                             address=self.ipv6)
            elif proto == 'ipv4':
                if self.behind_nat and public:
                    res = Record.objects.filter(
                        type='A', address=self.get_external_ipv4())
                    if res.count() < 1:
                        return unicode(self.get_external_ipv4())
                else:
                    res = self.record_set.filter(type='A',
                                                 address=self.ipv4)
            return unicode(res[0].fqdn)
        except:
            return None

    def list_ports(self):
        """
        Return a list of ports with forwarding rules set.
        """
        retval = []
        for rule in Rule.portforwards(host=self):
            forward = {
                'proto': rule.proto,
                'private': rule.dport,
            }

            if True:      # ipv4
                forward['ipv4'] = {
                    'host': self.get_hostname(proto='ipv4'),
                    'port': rule.get_external_port(proto='ipv4'),
                    'pk': rule.pk,
                }
            if self.ipv6:  # ipv6
                forward['ipv6'] = {
                    'host': self.get_hostname(proto='ipv6'),
                    'port': rule.get_external_port(proto='ipv6'),
                    'pk': rule.pk,
                }
            retval.append(forward)
        return retval

    def get_fqdn(self):
        """
        Get fully qualified host name of host.
        """
        return self.get_hostname('ipv4', public=False)

    def get_public_endpoints(self, port, protocol='tcp'):
        """Get public IPv4 and IPv6 endpoints for local port.

        Optionally the required protocol (e.g. TCP, UDP) can be specified.
        """
        endpoints = {}
        # IPv4
        ports = self.incoming_rules.filter(action='accept', dport=port,
                                           proto=protocol)
        public_port = (ports[0].get_external_port(proto='ipv4')
                       if ports.exists() else None)
        endpoints['ipv4'] = ((self.get_external_ipv4(), public_port)
                             if public_port else
                             None)
        # IPv6
        endpoints['ipv6'] = (self.ipv6, port) if public_port else None
        return endpoints

    def get_absolute_url(self):
        return reverse('network.host', kwargs={'pk': self.pk})

    @property
    def eui(self):
        return EUI(self.mac)

    @property
    def hw_vendor(self):
        try:
            return self.eui.oui.registration().org
        except:
            return None


class Firewall(models.Model):
    name = models.CharField(max_length=20, unique=True,
                            verbose_name=_('name'))

    class Meta:
        app_label = 'firewall'
        verbose_name = _("firewall")
        verbose_name_plural = _("firewalls")
        ordering = ('id', )

    def __unicode__(self):
        return self.name

    @method_cache(30)
    def get_remote_queue_name(self, queue_id="firewall"):
        """Returns the name of the remote celery queue for this node.

        Throws Exception if there is no worker on the queue.
        The result may include dead queues because of caching.
        """
        from .tasks.remote_tasks import check_queue

        if check_queue(self.name, queue_id, None):
            return self.name + "." + queue_id
        else:
            raise WorkerNotFound()

    @method_cache(20)
    def get_dhcp_clients(self):
        try:
            return get_dhcp_clients.apply_async(
                queue=self.get_remote_queue_name(), expires=60).get(timeout=2)
        except TimeoutError:
            logger.info("get_dhcp_clients task timed out")
        except IOError:
            logger.exception("get_dhcp_clients failed. "
                             "maybe syslog isn't readble by firewall worker")
        except:
            logger.exception("get_dhcp_clients failed")
        return {}

    def get_absolute_url(self):
        return reverse('network.firewall', kwargs={'pk': self.pk})


class Domain(models.Model):
    name = models.CharField(max_length=40, validators=[val_domain],
                            verbose_name=_('name'))
    owner = models.ForeignKey(User, verbose_name=_('owner'))
    created_at = models.DateTimeField(auto_now_add=True,
                                      verbose_name=_('created_at'))
    modified_at = models.DateTimeField(auto_now=True,
                                       verbose_name=_('modified_at'))
    ttl = models.IntegerField(default=600, verbose_name=_('ttl'))
    description = models.TextField(blank=True, verbose_name=_('description'))

    class Meta:
        app_label = 'firewall'
        verbose_name = _("domain")
        verbose_name_plural = _("domains")
        ordering = ('id', )

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('network.domain', kwargs={'pk': self.pk})


class Record(models.Model):
    CHOICES_type = (('A', 'A'), ('CNAME', 'CNAME'), ('AAAA', 'AAAA'),
                    ('MX', 'MX'), ('NS', 'NS'), ('PTR', 'PTR'), ('TXT', 'TXT'))
    name = models.CharField(max_length=40, validators=[val_domain_wildcard],
                            blank=True, null=True, verbose_name=_('name'))
    domain = models.ForeignKey('Domain', verbose_name=_('domain'))
    host = models.ForeignKey('Host', blank=True, null=True,
                             verbose_name=_('host'))
    type = models.CharField(max_length=6, choices=CHOICES_type,
                            verbose_name=_('type'))
    address = models.CharField(max_length=400,
                               verbose_name=_('address'))
    ttl = models.IntegerField(default=600, verbose_name=_('ttl'))
    owner = models.ForeignKey(User, verbose_name=_('owner'))
    description = models.TextField(blank=True, verbose_name=_('description'))
    created_at = models.DateTimeField(auto_now_add=True,
                                      verbose_name=_('created_at'))
    modified_at = models.DateTimeField(auto_now=True,
                                       verbose_name=_('modified_at'))

    def __unicode__(self):
        return self.desc()

    def desc(self):
        return u' '.join([self.fqdn, self.type, self.address])

    def save(self, *args, **kwargs):
        self.full_clean()
        super(Record, self).save(*args, **kwargs)

    def _validate_record(self):
        """Validate a record."""
        if not self.address:
            raise ValidationError(_("Address must be specified!"))

        try:
            validator = {
                'A': val_ipv4,
                'AAAA': val_ipv6,
                'CNAME': val_domain,
                'MX': val_mx,
                'NS': val_domain,
                'PTR': val_domain,
                'TXT': None,
            }[self.type]
        except KeyError:
            raise ValidationError(_("Unknown record type."))
        else:
            if validator:
                validator(self.address)

    def clean(self):
        """Validate the Record to be saved.
        """
        if self.name:
            self.name = self.name.rstrip(".")    # remove trailing dots

        self._validate_record()

    @property
    def fqdn(self):
        if self.name:
            return '%s.%s' % (self.name, self.domain.name)
        else:
            return self.domain.name

    def get_absolute_url(self):
        return reverse('network.record', kwargs={'pk': self.pk})

    class Meta:
        app_label = 'firewall'
        verbose_name = _("record")
        verbose_name_plural = _("records")
        ordering = (
            'domain',
            'name',
        )


class SwitchPort(models.Model):
    untagged_vlan = models.ForeignKey('Vlan',
                                      related_name='untagged_ports',
                                      verbose_name=_('untagged vlan'))
    tagged_vlans = models.ForeignKey('VlanGroup', blank=True, null=True,
                                     related_name='tagged_ports',
                                     verbose_name=_('tagged vlans'))
    description = models.TextField(blank=True, verbose_name=_('description'))
    created_at = models.DateTimeField(auto_now_add=True,
                                      verbose_name=_('created_at'))
    modified_at = models.DateTimeField(auto_now=True,
                                       verbose_name=_('modified_at'))

    class Meta:
        app_label = 'firewall'
        verbose_name = _("switch port")
        verbose_name_plural = _("switch ports")
        ordering = ('id', )

    def __unicode__(self):
        devices = ','.join(self.ethernet_devices.values_list('name',
                                                             flat=True))
        tagged_vlans = self.tagged_vlans.name if self.tagged_vlans else ''
        return 'devices=%s untagged=%s tagged=%s' % (devices,
                                                     self.untagged_vlan,
                                                     tagged_vlans)

    def get_absolute_url(self):
        return reverse('network.switch_port', kwargs={'pk': self.pk})


class EthernetDevice(models.Model):
    name = models.CharField(max_length=20,
                            unique=True,
                            verbose_name=_('interface'),
                            help_text=_('The name of network interface the '
                                        'gateway should serve this network '
                                        'on. For example eth2.'))
    switch_port = models.ForeignKey('SwitchPort',
                                    related_name='ethernet_devices',
                                    verbose_name=_('switch port'))
    created_at = models.DateTimeField(auto_now_add=True,
                                      verbose_name=_('created_at'))
    modified_at = models.DateTimeField(auto_now=True,
                                       verbose_name=_('modified_at'))

    class Meta:
        app_label = 'firewall'
        verbose_name = _("ethernet device")
        verbose_name_plural = _("ethernet devices")
        ordering = ('id', )

    def __unicode__(self):
        return self.name


class BlacklistItem(models.Model):
    ipv4 = models.GenericIPAddressField(
        protocol='ipv4', unique=True, verbose_name=("IPv4 address"))
    host = models.ForeignKey(
        'Host', blank=True, null=True, verbose_name=_('host'))
    reason = models.TextField(
        blank=True, null=True, verbose_name=_('reason'))
    snort_message = models.TextField(
        blank=True, null=True, verbose_name=_('short message'))

    whitelisted = models.BooleanField(
        default=False, verbose_name=_("whitelisted"))
    created_at = models.DateTimeField(auto_now_add=True,
                                      verbose_name=_('created_at'))
    modified_at = models.DateTimeField(auto_now=True,
                                       verbose_name=_('modified_at'))
    expires_at = models.DateTimeField(blank=True, null=True, default=None,
                                      verbose_name=_('expires at'))

    def save(self, *args, **kwargs):
        self.full_clean()
        super(BlacklistItem, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.ipv4

    class Meta(object):
        app_label = 'firewall'
        verbose_name = _('blacklist item')
        verbose_name_plural = _('blacklist items')
        ordering = ('id', )

    def get_absolute_url(self):
        return reverse('network.blacklist', kwargs={'pk': self.pk})


def send_task(sender, instance, created=False, **kwargs):
    reloadtask.apply_async(queue='localhost.man', args=[sender.__name__])


for sender in [Host, Rule, Domain, Record, Vlan, Firewall, Group,
               BlacklistItem, SwitchPort, EthernetDevice]:
    post_save.connect(send_task, sender=sender)
    post_delete.connect(send_task, sender=sender)
