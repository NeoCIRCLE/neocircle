import re
from datetime import datetime, timedelta
from itertools import product

from .models import (Host, Rule, Vlan, Domain, Record, Blacklist, SwitchPort)
from .iptables import IptRule, IptChain
import django.conf
from django.db.models import Q
from django.template import loader, Context


settings = django.conf.settings.FIREWALL_SETTINGS


class BuildFirewall:

    def __init__(self):
        self.chains = {}

    def add_rules(self, *args, **kwargs):
        for chain_name, ipt_rule in kwargs.items():
            if chain_name not in self.chains:
                self.create_chain(chain_name)
            self.chains[chain_name].add(ipt_rule)

    def create_chain(self, chain_name):
        self.chains[chain_name] = IptChain(name=chain_name)

    def build_ipt_nat(self):
        # portforward
        for rule in Rule.objects.filter(
                nat=True, direction='in').select_related('host'):
            self.add_rules(PREROUTING=IptRule(
                priority=1000,
                dst=(rule.get_external_ipv4(), None),
                proto=rule.proto,
                dport=rule.get_external_port('ipv4'),
                extra='-j DNAT --to-destination %s:%s' % (rule.host.ipv4,
                                                          rule.dport)))

        # default outbound NAT rules for VLANs
        for vl_in in Vlan.objects.exclude(
                snat_ip=None).prefetch_related('snat_to'):
            for vl_out in vl_in.snat_to.all():
                self.add_rules(POSTROUTING=IptRule(
                    priority=1000,
                    src=(vl_in.network4, None),
                    extra='-o %s -j SNAT --to-source %s' % (
                        vl_out.name, vl_in.snat_ip)))

    def ipt_filter_firewall(self):
        """Build firewall's own rules."""

        for rule in Rule.objects.exclude(firewall=None).select_related(
                'foreign_network').prefetch_related('foreign_network__vlans'):
            self.add_rules(**rule.get_ipt_rules())

    def ipt_filter_host_rules(self):
        """Build hosts' rules."""

        # host rules
        for rule in Rule.objects.exclude(host=None).select_related(
                'foreign_network', 'host',
                'host__vlan').prefetch_related('foreign_network__vlans'):
            self.add_rules(**rule.get_ipt_rules(rule.host))
        # group rules
        for rule in Rule.objects.exclude(hostgroup=None).select_related(
                'hostgroup', 'foreign_network').prefetch_related(
                'hostgroup__host_set__vlan', 'foreign_network__vlans'):
            for host in rule.hostgroup.host_set.all():
                self.add_rules(**rule.get_ipt_rules(host))

    def ipt_filter_vlan_rules(self):
        """Enable communication between VLANs."""

        for rule in Rule.objects.exclude(vlan=None).select_related(
                'vlan', 'foreign_network').prefetch_related(
                'foreign_network__vlans'):
            self.add_rules(**rule.get_ipt_rules())

    def ipt_filter_vlan_drop(self):
        """Close intra-VLAN chains."""

        for chain in self.chains.values():
            close_chain_rule = IptRule(priority=65534, action='LOG_DROP')
            chain.add(close_chain_rule)

    def ipt_filter_vlan_jump(self):
        """Create intra-VLAN jump rules."""

        vlans = Vlan.objects.all().values_list('name', flat=True)
        for vl_in, vl_out in product(vlans, repeat=2):
            name = '%s_%s' % (vl_in, vl_out)
            try:
                chain = self.chains[name]
            except KeyError:
                pass
            else:
                jump_rule = IptRule(priority=1, action=chain.name,
                                    extra='-i %s -o %s' % (vl_in, vl_out))
                self.add_rules(FORWARD=jump_rule)

    def build_ipt(self):
        """Build rules."""

        # TODO remove ipv4-specific rules

        self.ipt_filter_firewall()
        self.ipt_filter_host_rules()
        self.ipt_filter_vlan_rules()
        self.ipt_filter_vlan_jump()
        self.ipt_filter_vlan_drop()
        self.build_ipt_nat()

        context = {
            'filter': (chain for name, chain in self.chains.iteritems()
                       if chain.name not in ('PREROUTING', 'POSTROUTING')),
            'nat': (chain for name, chain in self.chains.iteritems()
                    if chain.name in ('PREROUTING', 'POSTROUTING'))}

        template = loader.get_template('firewall/iptables.conf')
        context['proto'] = 'ipv4'
        ipv4 = unicode(template.render(Context(context)))
        context['proto'] = 'ipv6'
        ipv6 = unicode(template.render(Context(context)))
        return (ipv4, ipv6)


def ipset():
    week = datetime.now() - timedelta(days=2)
    filter_ban = (Q(type='tempban', modified_at__gte=week) |
                  Q(type='permban')).values('ipv4', 'reason')
    return Blacklist.objects.filter(filter_ban)


def ipv6_to_octal(ipv6):
    while len(ipv6.split(':')) < 8:
        ipv6 = ipv6.replace('::', ':::')
    octets = []
    for part in ipv6.split(':'):
        if not part:
            octets.extend([0, 0])
        else:
            # Pad hex part to 4 digits.
            part = '%04x' % int(part, 16)
            octets.append(int(part[:2], 16))
            octets.append(int(part[2:], 16))
    return '\\' + '\\'.join(['%03o' % x for x in octets])


# =fqdn:ip:ttl          A, PTR
# &fqdn:ip:x:ttl        NS
# ZfqdnSOA
# +fqdn:ip:ttl          A
# ^                     PTR
# C                     CNAME
# :                     generic
# 'fqdn:s:ttl           TXT

def generate_ptr_records():
    DNS = []

    for host in Host.objects.order_by('vlan').all():
        template = host.vlan.reverse_domain
        i = host.get_external_ipv4().words
        reverse = (host.reverse if host.reverse not in [None, '']
                   else host.get_fqdn())

        # ipv4
        if host.ipv4:
            fqdn = template % {'a': i[0], 'b': i[1], 'c': i[2], 'd': i[3]}
            DNS.append("^%s:%s:%s" % (fqdn, reverse, settings['dns_ttl']))

        # ipv6
        if host.ipv6:
            DNS.append("^%s:%s:%s" % (host.ipv6.reverse_dns,
                                      reverse, settings['dns_ttl']))
        return DNS


def txt_to_octal(txt):
    return '\\' + '\\'.join(['%03o' % ord(x) for x in txt])


def generate_records():
    types = {'A': '+%(fqdn)s:%(address)s:%(ttl)s',
             'AAAA': ':%(fqdn)s:28:%(octal)s:%(ttl)s',
             'NS': '&%(fqdn)s::%(address)s:%(ttl)s',
             'CNAME': 'C%(fqdn)s:%(address)s:%(ttl)s',
             'MX': '@%(fqdn)s::%(address)s:%(dist)s:%(ttl)s',
             'PTR': '^%(fqdn)s:%(address)s:%(ttl)s',
             'TXT': '%(fqdn)s:%(octal)s:%(ttl)s'}

    retval = []

    for r in Record.objects.all():
        params = {'fqdn': r.fqdn, 'address': r.address, 'ttl': r.ttl}
        if r.type == 'MX':
            params['address'], params['dist'] = r.address.split(':', 2)
        if r.type == 'AAAA':
            params['octal'] = ipv6_to_octal(r.address)
        if r.type == 'TXT':
            params['octal'] = txt_to_octal(r.address)
        retval.append(types[r.type] % params)

    return retval


def dns():
    DNS = []

    # host PTR record
    DNS += generate_ptr_records()

    # domain SOA record
    for domain in Domain.objects.all():
        DNS.append("Z%s:%s:support.ik.bme.hu::::::%s" %
                   (domain.name, settings['dns_hostname'],
                    settings['dns_ttl']))

    # records
    DNS += generate_records()

    return DNS


def dhcp():
    regex = re.compile(r'^([0-9]+)\.([0-9]+)\.[0-9]+\.[0-9]+\s+'
                       r'([0-9]+)\.([0-9]+)\.[0-9]+\.[0-9]+$')
    DHCP = []

# /tools/dhcp3/dhcpd.conf.generated

    for i_vlan in Vlan.objects.all():
        if(i_vlan.dhcp_pool):
            m = regex.search(i_vlan.dhcp_pool)
            if(m or i_vlan.dhcp_pool == "manual"):
                DHCP.append('''
    # %(name)s - %(interface)s
    subnet %(net)s netmask %(netmask)s {
      %(extra)s;
      option domain-name "%(domain)s";
      option routers %(router)s;
      option domain-name-servers %(dnsserver)s;
      option ntp-servers %(ntp)s;
      next-server %(tftp)s;
      authoritative;
      filename \"pxelinux.0\";
      allow bootp; allow booting;
    }''' % {
                    'net': str(i_vlan.network4.network),
                    'netmask': str(i_vlan.network4.netmask),
                    'domain': i_vlan.domain,
                    'router': i_vlan.ipv4,
                    'ntp': i_vlan.ipv4,
                    'dnsserver': settings['rdns_ip'],
                    'extra': ("range %s" % i_vlan.dhcp_pool
                              if m else "deny unknown-clients"),
                    'interface': i_vlan.name,
                    'name': i_vlan.name,
                    'tftp': i_vlan.ipv4
                })

                for i_host in i_vlan.host_set.all():
                    DHCP.append('''
                    host %(hostname)s {
                      hardware ethernet %(mac)s;
                      fixed-address %(ipv4)s;
                    }''' % {
                        'hostname': i_host.hostname,
                        'mac': i_host.mac,
                        'ipv4': i_host.ipv4,
                    })

    return DHCP


def vlan():
    obj = Vlan.objects.values('vid', 'name', 'network4', 'network6')
    retval = {x['name']: {'tag': x['vid'],
                          'type': 'internal',
                          'interfaces': [x['name']],
                          'addresses': [str(x['network4']),
                                        str(x['network6'])]}
              for x in obj}
    for p in SwitchPort.objects.all():
        eth_count = p.ethernet_devices.count()
        if eth_count > 1:
            name = 'bond%d' % p.id
        elif eth_count == 1:
            name = p.ethernet_devices.get().name
        else:  # 0
            continue
        tag = p.untagged_vlan.vid
        retval[name] = {'tag': tag}
        if p.tagged_vlans is not None:
            trunk = list(p.tagged_vlans.vlans.values_list('vid', flat=True))
            retval[name]['trunks'] = sorted(trunk)
        retval[name]['interfaces'] = list(
            p.ethernet_devices.values_list('name', flat=True))
    return retval
