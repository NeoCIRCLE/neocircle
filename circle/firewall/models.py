# -*- coding: utf-8 -*-

from django.contrib.auth.models import User
from django.db import models
from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _
from firewall.fields import (MACAddressField, val_alfanum, val_reverse_domain,
                             val_domain, val_ipv4, val_ipv6, val_mx,
                             ipv4_2_ipv6, IPNetworkField)
from django.core.validators import MinValueValidator, MaxValueValidator
import django.conf
from django.db.models.signals import post_save
import random

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
    CHOICES_dir = (('0', 'out'), ('1', 'in'))

    direction = models.CharField(max_length=1, choices=CHOICES_dir,
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
    proto = models.CharField(max_length=10, choices=CHOICES_proto,
                             blank=True, null=True, verbose_name=_("protocol"),
                             help_text=_("Protocol of packets that match."))
    extra = models.TextField(blank=True, verbose_name=_("extra arguments"),
                             help_text=_("Additional arguments passed "
                                         "literally to the iptables-rule."))
    accept = models.BooleanField(default=False, verbose_name=_("accept"),
                                 help_text=_("Accept the matching packets "
                                             "(or deny if not checked)."))
    owner = models.ForeignKey(User, blank=True, null=True,
                              verbose_name=_("owner"),
                              help_text=_("The user responsible for "
                                          "this rule."))
    r_type = models.CharField(max_length=10, verbose_name=_("Rule type"),
                              choices=CHOICES_type,
                              help_text=_("The type of entity the rule "
                                          "belongs to."))
    nat = models.BooleanField(default=False, verbose_name=_("NAT"),
                              help_text=_("If network address translation "
                                          "shoud be done."))
    nat_dport = models.IntegerField(blank=True, null=True,
                                    help_text=_("Rewrite destination port "
                                                "number to this if NAT is "
                                                "needed."),
                                    validators=[MinValueValidator(1),
                                                MaxValueValidator(65535)])
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

    def desc(self):
        """Return a short string representation of the current rule.
        """
        return u'[%(type)s] %(src)s ▸ %(dst)s %(para)s %(desc)s' % {
            'type': self.r_type,
            'src': (unicode(self.foreign_network) if self.direction == '1'
                    else self.r_type),
            'dst': (self.r_type if self.direction == '1'
                    else unicode(self.foreign_network)),
            'para': ((("proto=%s " % self.proto) if self.proto else '') +
                     (("sport=%s " % self.sport) if self.sport else '') +
                     (("dport=%s " % self.dport) if self.dport else '')),
            'desc': self.description}

    @models.permalink
    def get_absolute_url(self):
        return ('network.rule', None, {'pk': self.pk})

    class Meta:
        verbose_name = _("rule")
        verbose_name_plural = _("rules")
        ordering = (
            'r_type',
            'direction',
            'proto',
            'sport',
            'dport',
            'nat_dport',
            'host',
        )


class Vlan(models.Model):

    """
    A vlan of the network,

    Networks controlled by this framework are split into separated subnets.
    These networks are izolated by the vlan (virtual lan) technology, which is
    commonly used by managed network switches to partition the network.

    Each vlan network has a unique identifier, a name, a unique IPv4 and IPv6
    range. The gateway also has an IP address in each range.
    """

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
    interface = models.CharField(max_length=20, unique=True,
                                 verbose_name=_('interface'), help_text=_(
                                     'The name of network interface the '
                                     'gateway should serve this network on. '
                                     'For example vlan0004 or eth2.'))
    network4 = IPNetworkField(unique=False,
                              version=4,
                              null=True,
                              blank=True,
                              verbose_name=_('IPv4 address/prefix'),
                              help_text=_(
                                  'The IPv4 address and the prefix length '
                                  'of the gateway.'
                                  'Recommended value is the last '
                                  'valid address of the subnet, '
                                  'for example '
                                  '10.4.255.254/16 for 10.4.0.0/16.'))
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
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('network.vlan', None, {'vid': self.vid})

    @property
    def net4(self):
        return self.network4.network

    @property
    def ipv4(self):
        return self.network4.ip

    @property
    def prefix4(self):
        return self.network4.prefixlen

    @property
    def net6(self):
        return self.network6.network

    @property
    def ipv6(self):
        return self.network6.ip

    @property
    def prefix6(self):
        return self.network6.prefixlen


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

    hostname = models.CharField(max_length=40, unique=True,
                                verbose_name=_('hostname'),
                                help_text=_('The alphanumeric hostname of '
                                            'the host, the first part of '
                                            'the FQDN.'),
                                validators=[val_alfanum])
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
    ipv4 = models.GenericIPAddressField(protocol='ipv4', unique=True,
                                        verbose_name=_('IPv4 address'),
                                        help_text=_(
                                            'The real IPv4 address of the '
                                            'host, for example 10.5.1.34.'))
    pub_ipv4 = models.GenericIPAddressField(
        protocol='ipv4', blank=True, null=True,
        verbose_name=_('WAN IPv4 address'),
        help_text=_('The public IPv4 address of the host on the wide '
                    'area network, if different.'))
    ipv6 = models.GenericIPAddressField(protocol='ipv6', unique=True,
                                        blank=True, null=True,
                                        verbose_name=_('IPv6 address'),
                                        help_text=_(
                                            'The global IPv6 address of the '
                                            'host, for example '
                                            '2001:500:88:200::10.'))
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

    def __unicode__(self):
        return self.hostname

    @property
    def incoming_rules(self):
        return self.rules.filter(direction='1')

    @property
    def outgoing_rules(self):
        return self.rules.filter(direction='0')

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
        if not id:
            Record(domain=self.vlan.domain, host=self, type='A',
                   owner=self.owner).save()
            if self.ipv6:
                Record(domain=self.vlan.domain, host=self, type='AAAA',
                       owner=self.owner).save()

    def enable_net(self):
        self.groups.add(Group.objects.get(name="netezhet"))

    def _get_ports_used(self, proto):
        """
        Gives a list of port numbers used for the public IP address of current
        host for the given protocol.

        :param proto: The transport protocol of the generated port (tcp|udp).
        :type proto: str.
        :returns: list -- list of int port numbers used.
        """
        if self.shared_ip:
            ports = Rule.objects.filter(host__pub_ipv4=self.pub_ipv4,
                                        nat=True, proto=proto)
        else:
            ports = self.rules.filter(proto=proto, )
        return ports.values_list('dport', flat=True)

    def _get_random_port(self, proto, used_ports=None):
        """
        Get a random unused port for given protocol for current host's public
        IP address.

        :param proto: The transport protocol of the generated port (tcp|udp).
        :type proto: str.
        :param used_ports: Optional list of used ports returned by
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

        vg = VlanGroup.objects.get(name=settings["default_vlangroup"])
        if self.shared_ip:
            if public < 1024:
                raise ValidationError(_("Only ports above 1024 can be used."))
            rule = Rule(direction='1', owner=self.owner, dport=public,
                        proto=proto, nat=True, accept=True, r_type="host",
                        nat_dport=private, host=self, foreign_network=vg)
        else:
            rule = Rule(direction='1', owner=self.owner, dport=public,
                        proto=proto, nat=False, accept=True, r_type="host",
                        host=self, foreign_network=vg)

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

        if self.shared_ip:
            self.rules.filter(owner=self.owner, proto=proto, host=self,
                              nat_dport=private).delete()
        else:
            self.rules.filter(owner=self.owner, proto=proto, host=self,
                              dport=private).delete()

    def get_hostname(self, proto):
        """
        Get a hostname for public ip address.

        :param proto: The IP version (ipv4|ipv6).
        :type proto: str.
        """
        assert proto in ('ipv6', 'ipv4', )
        try:
            if proto == 'ipv6':
                res = self.record_set.filter(type='AAAA')
            elif proto == 'ipv4':
                if self.shared_ip:
                    res = Record.objects.filter(type='A',
                                                address=self.pub_ipv4)
                else:
                    res = self.record_set.filter(type='A')
            return unicode(res[0].get_data()['name'])
        except:
            if self.shared_ip:
                return self.pub_ipv4
            else:
                return self.ipv4

    def list_ports(self):
        """
        Return a list of ports with forwarding rules set.
        """
        retval = []
        for rule in self.rules.filter(owner=self.owner):
            private = rule.nat_dport if self.shared_ip else rule.dport
            forward = {
                'proto': rule.proto,
                'private': private,
            }
            if self.shared_ip:
                public4 = rule.dport
                public6 = rule.nat_dport
            else:
                public4 = public6 = rule.dport

            if True:      # ipv4
                forward['ipv4'] = {
                    'host': self.get_hostname(proto='ipv4'),
                    'port': public4,
                }
            if self.ipv6:  # ipv6
                forward['ipv6'] = {
                    'host': self.get_hostname(proto='ipv6'),
                    'port': public6,
                }
            retval.append(forward)
        return retval

    def get_fqdn(self):
        """
        Get fully qualified host name of host.
        """
        return self.hostname + u'.' + unicode(self.vlan.domain)

    @models.permalink
    def get_absolute_url(self):
        return ('network.host', None, {'pk': self.pk})


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
    address = models.CharField(max_length=40, blank=True, null=True,
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
        a = self.get_data()
        return (u' '.join([a['name'], a['type'], a['address']])
                if a else _('(empty)'))

    def save(self, *args, **kwargs):
        self.full_clean()
        super(Record, self).save(*args, **kwargs)

    def _validate_w_host(self):
        """Validate a record with host set."""
        assert self.host
        if self.type in ['A', 'AAAA']:
            if self.address:
                raise ValidationError(_("Can't specify address for A "
                                        "or AAAA records if host is set!"))
            if self.name:
                raise ValidationError(_("Can't specify name for A "
                                        "or AAAA records if host is set!"))
        elif self.type == 'CNAME':
            if not self.name:
                raise ValidationError(_("Name must be specified for "
                                        "CNAME records if host is set!"))
            if self.address:
                raise ValidationError(_("Can't specify address for "
                                        "CNAME records if host is set!"))

    def _validate_wo_host(self):
        """Validate a record without a host set."""
        assert self.host is None

        if not self.address:
            raise ValidationError(_("Address must be specified!"))
        if self.type == 'A':
            val_ipv4(self.address)
        elif self.type == 'AAAA':
            val_ipv6(self.address)
        elif self.type in ['CNAME', 'NS', 'PTR', 'TXT']:
            val_domain(self.address)
        elif self.type == 'MX':
            val_mx(self.address)
        else:
            raise ValidationError(_("Unknown record type."))

    def clean(self):
        """Validate the Record to be saved.
        """
        if self.name:
            self.name = self.name.rstrip(".")    # remove trailing dots

        if self.host:
            self._validate_w_host()
        else:
            self._validate_wo_host()

    @property
    def fqdn(self):
        if self.host and self.type != 'MX':
            if self.type in ['A', 'AAAA']:
                return self.host.get_fqdn()
            elif self.type == 'CNAME':
                return self.name + '.' + unicode(self.domain)
            else:
                return self.name
        else:    # if self.host is None
            if self.name:
                return self.name + '.' + unicode(self.domain)
            else:
                return unicode(self.domain)

    def __get_address(self):
        if self.host:
            if self.type == 'A':
                return (self.host.pub_ipv4
                        if self.host.pub_ipv4 and not self.host.shared_ip
                        else self.host.ipv4)
            elif self.type == 'AAAA':
                return self.host.ipv6
            elif self.type == 'CNAME':
                return self.host.get_fqdn()
        # otherwise:
        return self.address

    def get_data(self):
        name = self.fqdn
        address = self.__get_address()
        if self.host and self.type == 'AAAA' and not self.host.ipv6:
            return None
        elif not address or not name:
            return None
        else:
            return {'name': name,
                    'type': self.type,
                    'ttl': self.ttl,
                    'address': address}

    @models.permalink
    def get_absolute_url(self):
        return ('network.record', None, {'pk': self.pk})

    class Meta:
        ordering = (
            'domain',
            'name',
        )


class Blacklist(models.Model):
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
        super(Blacklist, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.ipv4

    @models.permalink
    def get_absolute_url(self):
        return ('network.blacklist', None, {'pk': self.pk})


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