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

# from unittest import skip
from selenose.cases import SeleniumTestCase
# from django.test import TestCase
from xvfbwrapper import Xvfb
from firewall.models import Vlan, VlanGroup
from mock import Mock
from django_sshkey.models import UserKey
from vm.models import Instance
from django.contrib.auth.models import User, Group, Permission
import django.conf
settings = django.conf.settings.FIREWALL_SETTINGS
host = 'https:127.0.0.1'


class LoginMixin(object):
    def login(self, username, password='password'):
        driver = self.driver
        driver.get('%s/accounts/login/' % host)
        try:
            name_input = driver.find_element_by_id("id_username")
        except:
            pass
        try:
            password_input = driver.find_element_by_id("id_password")
        except:
            pass
        try:
            submit_input = driver.find_element_by_id("submit-id-submit")
        except:
            pass
        name_input.clear()
        name_input.send_keys(username)
        password_input.clear()
        password_input.send_keys(password)
        submit_input.click()

class VmDetailTest(LoginMixin, SeleniumTestCase):
    fixtures = ['test-vm-fixture.json', 'node.json']

    def setUp(self):
        self.xvfb = Xvfb(width=1280, height=720)
        self.addCleanup(self.xvfb.stop)
        self.xvfb.start()
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
        self.u1.user_permissions.add(Permission.objects.get(
            codename='create_vm'))
        settings["default_vlangroup"] = 'public'
        VlanGroup.objects.create(name='public')

    def tearDown(self):
        super(VmDetailTest, self).tearDown()
        self.u1.delete()
        self.u2.delete()
        self.us.delete()
        self.g1.delete()

    def test_404_vm_page(self):
        import sys
        self.login('user1')
        self.driver.get('%s/dashboard/' % host)
        print self.driver.page_source
        sys.stdout.flush()
        assert False
        # response = c.get('/dashboard/vm/235555/')
        # self.assertEqual(response.status_code, 404)
