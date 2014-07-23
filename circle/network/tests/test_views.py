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

from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User, Group
from mock import Mock

from dashboard.tests.test_views import LoginMixin

from vm.models import Instance
from firewall.models import Vlan, VlanGroup

import django.conf
settings = django.conf.settings.FIREWALL_SETTINGS


class VlanAclTest(LoginMixin, TestCase):
    fixtures = ['test-vm-fixture.json', 'node.json']

    def setUp(self):
        Instance.get_remote_queue_name = Mock(return_value='test')
        self.u1 = User.objects.create(username='user1')
        self.u1.set_password('password')
        self.u1.save()
        self.u2 = User.objects.create(username='user2', is_staff=True)
        self.u2.set_password('password')
        self.u2.save()
        self.us = User.objects.create(username='superuser', is_superuser=True)
        self.us.set_password('password')
        self.us.save()
        self.g1 = Group.objects.create(name='group1')
        self.g1.user_set.add(self.u1)
        self.g1.user_set.add(self.u2)
        self.g1.save()
        settings["default_vlangroup"] = 'public'
        VlanGroup.objects.create(name='public')

    def tearDown(self):
        super(VlanAclTest, self).tearDown()
        self.u1.delete()
        self.u2.delete()
        self.us.delete()
        self.g1.delete()

    def test_add_new_user_permission(self):
        c = Client()
        self.login(c, "superuser")
        vlan = Vlan.objects.get(vid=1)
        self.assertEqual([], vlan.get_users_with_level())

        resp = c.post("/network/vlans/2/acl/", {
            'name': "user1",
            'level': "user",
        })

        vlan = Vlan.objects.get(vid=1)
        self.assertTrue((self.u1, "user") in vlan.get_users_with_level())
        self.assertEqual(resp.status_code, 302)

    def test_make_user_operator(self):
        c = Client()
        self.login(c, "superuser")
        vlan = Vlan.objects.get(vid=1)

        vlan.set_level(self.u1, "user")
        self.assertTrue((self.u1, "user") in vlan.get_users_with_level())

        resp = c.post("/network/vlans/2/acl/", {
            'perm-u-%d' % self.u1.pk: "operator",
            'level': "",
            'name': "",
        })

        self.assertTrue((self.u1, "operator") in vlan.get_users_with_level())
        self.assertEqual(resp.status_code, 302)

    def test_remove_user_permission(self):
        c = Client()
        self.login(c, "superuser")
        vlan = Vlan.objects.get(vid=1)

        vlan.set_level(self.u1, "user")
        self.assertTrue((self.u1, "user") in vlan.get_users_with_level())

        resp = c.post("/network/vlans/2/acl/", {
            'remove-u-%d' % self.u1.pk: "",
            'level': "",
            'name': "",
        })

        self.assertTrue((self.u1, "user") not in vlan.get_users_with_level())
        self.assertEqual(resp.status_code, 302)
