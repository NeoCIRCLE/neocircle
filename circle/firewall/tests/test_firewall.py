from netaddr import IPSet

from django.test import TestCase
from django.contrib.auth.models import User
from ..admin import HostAdmin
from firewall.models import Vlan, Domain, Record, Host
from django.forms import ValidationError


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
                      pub_ipv4=self.vlan.snat_ip)
        self.h.save()

    def test_issue_93_wo_record(self):
        self.assertEqual(self.h.get_hostname(proto='ipv4', public=True),
                         unicode(self.h.pub_ipv4))

    def test_issue_93_w_record(self):
        self.r = Record(name='vm', type='A', domain=self.d, owner=self.u1,
                        address=self.vlan.snat_ip)
        self.r.save()
        self.assertEqual(self.h.get_hostname(proto='ipv4', public=True),
                         self.r.fqdn)
