from django.test import TestCase
from django.contrib.auth.models import User
from ..admin import HostAdmin
from firewall.models import Vlan, Domain, Host
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

    def test_new_addr_last(self):
        self.assertEqual(self.vlan.get_new_address()['ipv4'], '10.0.0.6')

    def test_new_addr_w_overflow(self):
        Host(hostname='h-6', mac='01:02:03:04:05:06',
             ipv4='10.0.0.6', vlan=self.vlan, owner=self.u1).save()
        self.assertEqual(self.vlan.get_new_address()['ipv4'], '10.0.0.2')
