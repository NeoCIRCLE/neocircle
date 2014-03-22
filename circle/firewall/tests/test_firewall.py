from netaddr import IPSet, AddrFormatError

from django.test import TestCase
from django.contrib.auth.models import User
from ..admin import HostAdmin
from firewall.models import Vlan, Domain, Record, Host
from firewall.fw import dns, ipv6_to_octal
from django.forms import ValidationError
from ..iptables import IptRule, IptChain, InvalidRuleExcepion


class MockInstance:
    def __init__(self, groups):
        self.groups = MockGroups(groups)


class MockGroup:
    def __init__(self, name):
        self.name = name


class MockGroups:
    def __init__(self, groups):
        self.groups = groups

    def all(self):
        return self.groups


class HostAdminTestCase(TestCase):
    def test_no_groups(self):
        instance = MockInstance([])
        l = HostAdmin.list_groups(instance)
        self.assertEqual(l, "")

    def test_sigle_group(self):
        instance = MockInstance([MockGroup("alma")])
        l = HostAdmin.list_groups(instance)
        self.assertEqual(l, "alma")

    def test_multiple_groups(self):
        instance = MockInstance([MockGroup("alma"),
                                 MockGroup("korte"), MockGroup("szilva")])
        l = HostAdmin.list_groups(instance)
        self.assertEqual(l, "alma, korte, szilva")


class GetNewAddressTestCase(TestCase):
    def setUp(self):
        self.u1 = User.objects.create(username='user1')
        self.u1.save()
        d = Domain(name='example.org', owner=self.u1)
        d.save()
        # /29 = .1-.6 =  6 hosts/subnet + broadcast + network id
        self.vlan = Vlan(vid=1, name='test', network4='10.0.0.0/29',
                         network6='2001:738:2001:4031::/80', domain=d,
                         owner=self.u1)
        self.vlan.save()
        self.vlan.host_set.all().delete()
        for i in [1] + range(3, 6):
            Host(hostname='h-%d' % i, mac='01:02:03:04:05:%02d' % i,
                 ipv4='10.0.0.%d' % i, vlan=self.vlan,
                 owner=self.u1).save()

    def test_new_addr_w_empty_vlan(self):
        self.vlan.host_set.all().delete()
        self.vlan.get_new_address()

    def test_all_addr_in_use(self):
        for i in (2, 6):
            Host(hostname='h-%d' % i, mac='01:02:03:04:05:%02d' % i,
                 ipv4='10.0.0.%d' % i, vlan=self.vlan,
                 owner=self.u1).save()
        self.assertRaises(ValidationError, self.vlan.get_new_address)

    def test_all_addr_in_use_w_ipv6(self):
        Host(hostname='h-x', mac='01:02:03:04:05:06',
             ipv4='10.0.0.6', ipv6='2001:738:2001:4031:0:0:2:0',
             vlan=self.vlan, owner=self.u1).save()
        self.assertRaises(ValidationError, self.vlan.get_new_address)

    def test_new_addr(self):
        used_v4 = IPSet(self.vlan.host_set.values_list('ipv4', flat=True))
        assert self.vlan.get_new_address()['ipv4'] not in used_v4


class HostGetHostnameTestCase(TestCase):
    def setUp(self):
        self.u1 = User.objects.create(username='user1')
        self.u1.save()
        self.d = Domain(name='example.org', owner=self.u1)
        self.d.save()
        Record.objects.all().delete()
        self.vlan = Vlan(vid=1, name='test', network4='10.0.0.0/24',
                         network6='2001:738:2001:4031::/80', domain=self.d,
                         owner=self.u1, network_type='portforward',
                         snat_ip='10.1.1.1')
        self.vlan.save()
        self.h = Host(hostname='h', mac='01:02:03:04:05:00', ipv4='10.0.0.1',
                      vlan=self.vlan, owner=self.u1, shared_ip=True,
                      external_ipv4=self.vlan.snat_ip)
        self.h.save()

    def test_issue_93_wo_record(self):
        self.assertEqual(self.h.get_hostname(proto='ipv4', public=True),
                         unicode(self.h.external_ipv4))

    def test_issue_93_w_record(self):
        self.r = Record(name='vm', type='A', domain=self.d, owner=self.u1,
                        address=self.vlan.snat_ip)
        self.r.save()
        self.assertEqual(self.h.get_hostname(proto='ipv4', public=True),
                         self.r.fqdn)


class IptablesTestCase(TestCase):
    def setUp(self):
        self.r = [IptRule(priority=4, action='ACCEPT',
                          src=('127.0.0.4', None)),
                  IptRule(priority=4, action='ACCEPT',
                          src=('127.0.0.4', None)),
                  IptRule(priority=2, action='ACCEPT',
                          dst=('127.0.0.2', None),
                          extra='-p icmp'),
                  IptRule(priority=6, action='ACCEPT',
                          dst=('127.0.0.6', None),
                          proto='tcp', dport=80),
                  IptRule(priority=1, action='ACCEPT',
                          dst=('127.0.0.1', None),
                          proto='udp', dport=53),
                  IptRule(priority=5, action='ACCEPT',
                          dst=('127.0.0.5', None),
                          proto='tcp', dport=443),
                  IptRule(priority=2, action='ACCEPT',
                          dst=('127.0.0.2', None),
                          proto='icmp'),
                  IptRule(priority=6, action='ACCEPT',
                          dst=('127.0.0.6', None),
                          proto='tcp', dport='1337')]

    def test_chain_add(self):
        ch = IptChain(name='test')
        ch.add(*self.r)
        self.assertEqual(len(ch), len(self.r) - 1)

    def test_rule_compile_ok(self):
        self.assertEqual(self.r[5].compile(),
                         '-d 127.0.0.5 -p tcp --dport 443 -g ACCEPT')

    def test_rule_compile_fail(self):
        self.assertRaises(InvalidRuleExcepion,
                          IptRule, **{'priority': 5, 'action': 'ACCEPT',
                                      'dst': '127.0.0.5',
                                      'proto': 'icmp', 'dport': 443})

    def test_chain_compile(self):
        ch = IptChain(name='test')
        ch.add(*self.r)
        compiled = ch.compile()
        self.assertEqual(len(compiled.splitlines()), len(ch))


class DnsTestCase(TestCase):
    def setUp(self):
        self.u1 = User.objects.create(username='user1')
        self.u1.save()
        d = Domain(name='example.org', owner=self.u1)
        d.save()
        self.vlan = Vlan(vid=1, name='test', network4='10.0.0.0/29',
                         network6='2001:738:2001:4031::/80', domain=d,
                         owner=self.u1)
        self.vlan.save()
        for i in range(1, 6):
            Host(hostname='h-%d' % i, mac='01:02:03:04:05:%02d' % i,
                 ipv4='10.0.0.%d' % i, vlan=self.vlan,
                 owner=self.u1).save()
        self.r1 = Record(name='tst', type='A', address='127.0.0.1',
                         domain=d, owner=self.u1)
        self.rb = Record(name='tst', type='AAAA', address='1.0.0.1',
                         domain=d, owner=self.u1)
        self.r2 = Record(name='ts', type='AAAA', address='2001:123:45::6',
                         domain=d, owner=self.u1)
        self.r1.save()
        self.r2.save()

    def test_bad_aaaa_record(self):
        self.assertRaises(AddrFormatError, ipv6_to_octal, self.rb.address)

    def test_good_aaaa_record(self):
        ipv6_to_octal(self.r2.address)

    def test_dns_func(self):
        records = dns()
        self.assertEqual(Host.objects.count() * 2 +         # soa
                         len((self.r1, self.r2)) + 1,
                         len(records))
