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

from mock import patch
from netaddr import IPSet, AddrFormatError

import django.conf
from django.contrib.auth.models import User
from django.forms import ValidationError
from django.test import TestCase

from common.tests.celery_mock import MockCeleryMixin
from firewall.admin import HostAdmin
from firewall.fw import dns, ipv6_to_octal
from firewall.iptables import IptRule, IptChain, InvalidRuleExcepion
from firewall.models import (Vlan, Domain, Record, Host, VlanGroup, Group,
                             Rule, Firewall)
from firewall.tasks.local_tasks import reloadtask_worker, reloadtask

settings = django.conf.settings.FIREWALL_SETTINGS


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


class GetNewAddressTestCase(MockCeleryMixin, TestCase):
    def setUp(self):
        self.u1 = User.objects.create(username='user1')
        self.u1.save()
        d = Domain(name='example.org', owner=self.u1)
        d.save()
        # /29 = .1-.6 =  6 hosts/subnet + broadcast + network id
        self.vlan = Vlan(vid=1, name='test', network4='10.0.0.1/29',
                         network6='2001:738:2001:4031::/80', domain=d,
                         owner=self.u1)
        self.vlan.clean()
        self.vlan.save()
        self.vlan.host_set.all().delete()
        for i in range(3, 6):
            Host(hostname='h-%d' % i, mac='01:02:03:04:05:%02d' % i,
                 ipv4='10.0.0.%d' % i, vlan=self.vlan,
                 owner=self.u1).save()

    def tearDown(self):
        self.vlan.delete()

    def test_new_addr_w_empty_vlan(self):
        self.vlan.host_set.all().delete()
        self.vlan.get_new_address()

    def test_all_addr_in_use(self):
        for i in (2, 6):
            Host(hostname='h-%d' % i, mac='01:02:03:04:05:%02d' % i,
                 ipv4='10.0.0.%d' % i, vlan=self.vlan,
                 owner=self.u1).save()
        self.assertRaises(ValidationError, self.vlan.get_new_address)

    def test_all_addr_in_use2(self):
        Host(hostname='h-xd', mac='01:02:03:04:05:06',
             ipv4='10.0.0.6', vlan=self.vlan,
             owner=self.u1).save()
        Host(hostname='h-arni', mac='01:02:03:04:05:02',
             ipv4='100.0.0.1', vlan=self.vlan, external_ipv4='10.0.0.2',
             owner=self.u1).save()
        self.assertRaises(ValidationError, self.vlan.get_new_address)

    def test_new_addr(self):
        used_v4 = IPSet(self.vlan.host_set.values_list('ipv4', flat=True))
        assert self.vlan.get_new_address()['ipv4'] not in used_v4


class HostGetHostnameTestCase(MockCeleryMixin, TestCase):
    def setUp(self):
        self.u1 = User.objects.create(username='user1')
        self.u1.save()
        self.d = Domain(name='example.org', owner=self.u1)
        self.d.save()
        Record.objects.all().delete()
        self.vlan = Vlan(vid=1, name='test', network4='10.0.0.1/24',
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
        assert unicode(self.r[5])
        self.assertEqual(self.r[5].compile(),
                         '-d 127.0.0.5 -p tcp --dport 443 -g ACCEPT')

    def test_rule_compile_fail(self):
        self.assertRaises(InvalidRuleExcepion,
                          IptRule, **{'proto': 'test'})
        self.assertRaises(InvalidRuleExcepion,
                          IptRule, **{'priority': 5, 'action': 'ACCEPT',
                                      'dst': '127.0.0.5',
                                      'proto': 'icmp', 'dport': 443})

    def test_chain_compile(self):
        ch = IptChain(name='test')
        ch.add(*self.r)
        compiled = ch.compile()
        compiled_v6 = ch.compile_v6()
        assert unicode(ch)
        self.assertEqual(len(compiled.splitlines()), len(ch))
        self.assertEqual(len(compiled_v6.splitlines()), 0)


class ReloadTestCase(MockCeleryMixin, TestCase):
    def setUp(self):
        self.u1 = User.objects.create(username='user1')
        self.u1.save()
        d = Domain.objects.create(name='example.org', owner=self.u1)
        self.vlan = Vlan(vid=1, name='test', network4='10.0.0.1/29',
                         snat_ip='152.66.243.99',
                         network6='2001:738:2001:4031::/80', domain=d,
                         owner=self.u1, network_type='portforward',
                         dhcp_pool='manual')
        self.vlan.save()
        self.vlan2 = Vlan(vid=2, name='pub', network4='10.1.0.1/29',
                          network6='2001:738:2001:4032::/80', domain=d,
                          owner=self.u1, network_type='public')
        self.vlan2.save()
        self.vlan.snat_to.add(self.vlan2)

        settings["default_vlangroup"] = 'public'
        settings["default_host_groups"] = ['netezhet']
        vlg = VlanGroup.objects.create(name='public')
        vlg.vlans.add(self.vlan, self.vlan2)
        self.hg = Group.objects.create(name='netezhet')
        Rule.objects.create(action='accept', hostgroup=self.hg,
                            foreign_network=vlg)

        firewall = Firewall.objects.create(name='fw')
        Rule.objects.create(action='accept', firewall=firewall,
                            foreign_network=vlg)

        for i in range(1, 6):
            h = Host.objects.create(hostname='h-%d' % i, vlan=self.vlan,
                                    mac='01:02:03:04:05:%02d' % i,
                                    ipv4='10.0.0.%d' % i, owner=self.u1)
            h.enable_net()
            h.groups.add(self.hg)
            if i == 5:
                h.vlan = self.vlan2
                h.save()
                self.h5 = h
            if i == 1:
                self.h1 = h

        self.r1 = Record(name='tst', type='A', address='127.0.0.1',
                         domain=d, owner=self.u1)
        self.rb = Record(name='tst', type='AAAA', address='1.0.0.1',
                         domain=d, owner=self.u1)
        self.r2 = Record(name='ts', type='AAAA', address='2001:123:45::6',
                         domain=d, owner=self.u1)
        self.rm = Record(name='asd', type='MX', address='10:teszthu',
                         domain=d, owner=self.u1)
        self.rt = Record(name='asd', type='TXT', address='ASD',
                         domain=d, owner=self.u1)
        self.r1.save()
        self.r2.save()
        with patch('firewall.models.Record.clean'):
            self.rb.save()
        self.rm.save()
        self.rt.save()

    def tearDown(self):
        settings["default_host_groups"] = []

    def test_bad_aaaa_record(self):
        self.assertRaises(AddrFormatError, ipv6_to_octal, self.rb.address)

    def test_good_aaaa_record(self):
        ipv6_to_octal(self.r2.address)

    def test_dns_func(self):
        records = dns()
        self.assertEqual(Host.objects.count() * 2 +         # soa
                         len((self.r1, self.r2, self.rm, self.rt)) + 1,
                         len(records))

    def test_host_add_port(self):
        h = self.h1
        h.ipv6 = '2001:2:3:4::0'
        assert h.behind_nat
        h.save()
        old_rules = h.rules.count()
        h.add_port('tcp', private=22)
        new_rules = h.rules.count()
        self.assertEqual(new_rules, old_rules + 1)
        self.assertEqual(len(h.list_ports()), old_rules + 1)
        endp = h.get_public_endpoints(22)
        self.assertEqual(endp['ipv4'][0], h.ipv4)
        assert int(endp['ipv4'][1])
        self.assertEqual(endp['ipv6'][0], h.ipv6)
        assert int(endp['ipv6'][1])

    def test_host_add_port2(self):
        h = self.h5
        h.ipv6 = '2001:2:3:4::1'
        h.save()
        assert not h.behind_nat
        old_rules = h.rules.count()
        h.add_port('tcp', private=22)
        new_rules = h.rules.count()
        self.assertEqual(new_rules, old_rules + 1)
        self.assertEqual(len(h.list_ports()), old_rules + 1)
        endp = h.get_public_endpoints(22)
        self.assertEqual(endp['ipv4'][0], h.ipv4)
        assert int(endp['ipv4'][1])
        self.assertEqual(endp['ipv6'][0], h.ipv6)
        assert int(endp['ipv6'][1])

    def test_host_del_port(self):
        h = self.h1
        h.ipv6 = '2001:2:3:4::0'
        h.save()
        h.add_port('tcp', private=22)
        old_rules = h.rules.count()
        h.del_port('tcp', private=22)
        new_rules = h.rules.count()
        self.assertEqual(new_rules, old_rules - 1)

    def test_host_add_port_wo_vlangroup(self):
        VlanGroup.objects.filter(name='public').delete()
        h = self.h1
        old_rules = h.rules.count()
        h.add_port('tcp', private=22)
        new_rules = h.rules.count()
        self.assertEqual(new_rules, old_rules)

    def test_periodic_task(self):
        # TODO
        cache = patch('firewall.tasks.local_tasks.cache')
        grqn = patch('firewall.models.Firewall.get_remote_queue_name',
                     return_value='fw.firewall')
        worker = patch(
            'firewall.tasks.local_tasks.reloadtask_worker.apply_async')

        dns = patch('firewall.tasks.remote_tasks.reload_dns.apply_async')
        fw = patch(
            'firewall.tasks.remote_tasks.reload_firewall.apply_async')
        fw_vlan = patch(
            'firewall.tasks.remote_tasks.reload_firewall_vlan.apply_async')
        blacklist = patch(
            'firewall.tasks.remote_tasks.reload_blacklist.apply_async')
        dhcp = patch('firewall.tasks.remote_tasks.reload_dhcp.apply_async')

        with cache as cache, grqn, dns, fw, fw_vlan, blacklist, dhcp, worker:
            self.test_host_add_port()
            self.test_host_add_port2()
            reloadtask_worker()
            reloadtask()
            assert cache.delete.called
