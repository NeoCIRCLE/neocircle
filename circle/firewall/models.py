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

from itertools import islice, ifilter
import logging
from netaddr import IPSet, EUI, IPNetwork

from django.contrib.auth.models import User
from django.db import models
from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _
from firewall.fields import (MACAddressField, val_alfanum, val_reverse_domain,
                             val_ipv6_template, val_domain, val_ipv4,
                             val_ipv6, val_mx, convert_ipv4_to_ipv6,
                             IPNetworkField, IPAddressField)
from django.core.validators import MinValueValidator, MaxValueValidator
import django.conf
from django.db.models.signals import post_save, post_delete
import random

from common.models import HumanSortField
from firewall.tasks.local_tasks import reloadtask
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

    @models.permalink
    def get_absolute_url(self):
        return ('network.rule', None, {'pk': self.pk})

    @staticmethod
    def get_chain_name(local, remote, direction):
        if direction == 'in':
            # remote -> local
            return '%s_%s' % (remote, local)
        else:
            # local -> remote
            return '%s_%s' % (local, remote)

    def get_ipt_rules(self, host=None):
        # action
        action = 'LOG_ACC' if self.action == 'accept' else 'LOG_DROP'

        # src and dst addresses
        src = None
        dst = None

        if host:
            ip = (host.ipv4, host.ipv6_with_prefixlen)
            if self.direction == 'in':
                dst = ip
            else:
                src = ip

        # src and dst ports
        if self.direction == 'in':
            dport = self.dport
            sport = self.sport
        else:
            dport = self.sport
            sport = self.dport

        # 'chain_name': rule dict
        retval = {}

        # process foreign vlans
        for foreign_vlan in self.foreign_network.vlans.all():
            r = IptRule(priority=self.weight, action=action,
                        proto=self.proto, extra=self.extra,
                        comment='Rule #%s' % self.pk,
                        src=src, dst=dst, dport=dport, sport=sport)
            # host, hostgroup or vlan rule
            if host or self.vlan_id:
                local_vlan = host.vlan.name if host else self.vlan.name
                chain_name = Rule.get_chain_name(local=local_vlan,
                                                 remote=foreign_vlan.name,
                                                 direction=self.direction)
            # firewall rule
            elif self.firewall_id:
                chain_name = 'INPUT' if self.direction == 'in' else 'OUTPUT'

            retval[chain_name] = r

        return retval

    class Meta:
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
                                     null=True, verbose_name=_('NAT to'),
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
        validators=[val_ipv6_template],
        verbose_name=_('ipv6 template'),
        default="2001:738:2001:4031:%(b)d:%(c)d:%(d)d:0")
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

    def __unicode__(self):
        return "%s - %s" % ("managed" if self.managed else "unmanaged",
                            self.name)

    @models.permalink
    def get_absolute_url(self):
        return ('network.vlan', None, {'vid': self.vid})

    def get_random_addresses(self, used_v4, buffer_size=100, max_hosts=10000):
        addresses = islice(self.network4.iter_hosts(), max_hosts)
        unused_addresses = list(islice(
            ifilter(lambda x: x not in used_v4, addresses), buffer_size))
        random.shuffle(unused_addresses)
        return unused_addresses

    def get_new_address(self):
        hosts = self.host_set
        used_v4 = IPSet(hosts.values_list('ipv4', flat=True))
        used_v6 = IPSet(hosts.exclude(ipv6__isnull=True)
                        .values_list('ipv6', flat=True))

        for ipv4 in self.get_random_addresses(used_v4):
            logger.debug("Found unused IPv4 address %s.", ipv4)
            ipv6 = None
            if self.network6 is not None:
                ipv6 = convert_ipv4_to_ipv6(self.ipv6_template, ipv4)
                if ipv6 in used_v6:
                    continue
                else:
                    logger.debug("Found unused IPv6 address %s.", ipv6)
            return {'ipv4': ipv4, 'ipv6': ipv6}
        else:
            raise ValidationError(_("All IP addresses are already in use."))


class VlanGroup(models.Model):
    """
    A group of Vlans.
    """

    name = models.CharField(max_length=20, unique=True, verbose_name=_('name'),
                            help_text=_('The name of the group.'))
    vlans = models.ManyToManyField('Vlan', symmetrical=False, blank=True,
                                   null=True, verbose_name=_('vlans'),
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

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('network.vlan_group', None, {'pk': self.pk})


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

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('network.group', None, {'pk': self.pk})


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
                                    null=True, verbose_name=_('groups'),
                                    help_text=_(
                                        'Host groups the machine is part of.'))
    created_at = models.DateTimeField(auto_now_add=True,
                                      verbose_name=_('created at'))
    modified_at = models.DateTimeField(auto_now=True,
                                       verbose_name=_('modified at'))

    class Meta(object):
        unique_together = ('hostname', 'vlan')
        ordering = ('normalized_hostname', 'vlan')

    def __unicode__(self):
        return self.hostname

    @property
    def incoming_rules(self):
        return self.rules.filter(direction='in')

    @property
    def ipv6_with_prefixlen(self):
        try:
            net = IPNetwork(self.ipv6)
            net.prefixlen = self.vlan.host_ipv6_prefixlen
            return net
        except TypeError:
            return None

    def get_external_ipv4(self):
        return self.external_ipv4 if self.external_ipv4 else self.ipv4

    @property
    def behind_nat(self):
        return self.vlan.network_type != 'public'

    def clean(self):
        if (self.external_ipv4 and not self.shared_ip and self.behind_nat
                and Host.objects.exclude(id=self.id).filter(
                    external_ipv4=self.external_ipv4)):
            raise ValidationError(_("If shared_ip has been checked, "
                                    "external_ipv4 has to be unique."))
        if Host.objects.exclude(id=self.id).filter(external_ipv4=self.ipv4):
            raise ValidationError(_("You can't use another host's NAT'd "
                                    "address as your own IPv4."))

    def save(self, *args, **kwargs):
        if not self.id and self.ipv6 == "auto":
            self.ipv6 = convert_ipv4_to_ipv6(self.vlan.ipv6_template,
                                             self.ipv4)
        self.full_clean()

        super(Host, self).save(*args, **kwargs)

        # IPv4
        if self.ipv4 is not None:
            # update existing records
            affected_records = Record.objects.filter(
                host=self, name=self.hostname,
                type='A').update(address=self.ipv4)
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
                if public < 1024:
                    raise ValidationError(
                        _("Only ports above 1024 can be used."))
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

        self.rules.filter(owner=self.owner, proto=proto, host=self,
                          dport=private).delete()

    def get_hostname(self, proto, public=True):
        """
        Get a private or public hostname for host.

        :param proto: The IP version (ipv4|ipv6).
        :type proto: str.
        """
        assert proto in ('ipv6', 'ipv4', )
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
        for rule in self.rules.filter(owner=self.owner):
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
        blocked = self.incoming_rules.exclude(
            action='accept').filter(dport=port, proto=protocol).exists()
        endpoints['ipv6'] = (self.ipv6, port) if not blocked else None
        return endpoints

    @models.permalink
    def get_absolute_url(self):
        return ('network.host', None, {'pk': self.pk})

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

    def __unicode__(self):
        return self.name


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

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('network.domain', None, {'pk': self.pk})


class Record(models.Model):
    CHOICES_type = (('A', 'A'), ('CNAME', 'CNAME'), ('AAAA', 'AAAA'),
                   ('MX', 'MX'), ('NS', 'NS'), ('PTR', 'PTR'), ('TXT', 'TXT'))
    name = models.CharField(max_length=40, validators=[val_domain],
                            blank=True, null=True, verbose_name=_('name'))
    domain = models.ForeignKey('Domain', verbose_name=_('domain'))
    host = models.ForeignKey('Host', blank=True, null=True,
                             verbose_name=_('host'))
    type = models.CharField(max_length=6, choices=CHOICES_type,
                            verbose_name=_('type'))
    address = models.CharField(max_length=200,
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

    @models.permalink
    def get_absolute_url(self):
        return ('network.record', None, {'pk': self.pk})

    class Meta:
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

    def __unicode__(self):
        devices = ','.join(self.ethernet_devices.values_list('name',
                                                             flat=True))
        tagged_vlans = self.tagged_vlans.name if self.tagged_vlans else ''
        return 'devices=%s untagged=%s tagged=%s' % (devices,
                                                     self.untagged_vlan,
                                                     tagged_vlans)

    @models.permalink
    def get_absolute_url(self):
        return ('network.switch_port', None, {'pk': self.pk})


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

    def __unicode__(self):
        return self.name


class BlacklistItem(models.Model):
    CHOICES_type = (('permban', 'permanent ban'), ('tempban', 'temporary ban'),
                    ('whitelist', 'whitelist'), ('tempwhite', 'tempwhite'))
    ipv4 = models.GenericIPAddressField(protocol='ipv4', unique=True)
    host = models.ForeignKey('Host', blank=True, null=True,
                             verbose_name=_('host'))
    reason = models.TextField(blank=True, verbose_name=_('reason'))
    snort_message = models.TextField(blank=True,
                                     verbose_name=_('short message'))
    type = models.CharField(
        max_length=10,
        choices=CHOICES_type,
        default='tempban',
        verbose_name=_('type')
    )
    created_at = models.DateTimeField(auto_now_add=True,
                                      verbose_name=_('created_at'))
    modified_at = models.DateTimeField(auto_now=True,
                                       verbose_name=_('modified_at'))

    def save(self, *args, **kwargs):
        self.full_clean()
        super(BlacklistItem, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.ipv4

    class Meta(object):
        verbose_name = _('blacklist item')
        verbose_name_plural = _('blacklist')

    @models.permalink
    def get_absolute_url(self):
        return ('network.blacklist', None, {'pk': self.pk})


def send_task(sender, instance, created=False, **kwargs):
    reloadtask.apply_async(queue='localhost.man', args=[sender.__name__])


for sender in [Host, Rule, Domain, Record, Vlan, Firewall, Group,
               BlacklistItem, SwitchPort, EthernetDevice]:
    post_save.connect(send_task, sender=sender)
    post_delete.connect(send_task, sender=sender)
