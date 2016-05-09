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

import json

# from unittest import skip
from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth import authenticate

from common.tests.celery_mock import MockCeleryMixin
from dashboard.views import VmAddInterfaceView
from vm.models import Instance, InstanceTemplate, Lease, Node, Trait
from vm.operations import (WakeUpOperation, AddInterfaceOperation,
                           AddPortOperation, RemoveInterfaceOperation,
                           DeployOperation)
from ..models import Profile
from firewall.models import Vlan, Host, VlanGroup
from mock import Mock, patch
from django_sshkey.models import UserKey

import django.conf
settings = django.conf.settings.FIREWALL_SETTINGS


class LoginMixin(object):
    def login(self, client, username, password='password'):
        response = client.post('/accounts/login/', {'username': username,
                                                    'password': password})
        self.assertNotEqual(response.status_code, 403)


class VmDetailTest(LoginMixin, MockCeleryMixin, TestCase):
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
        c = Client()
        self.login(c, 'user1')
        response = c.get('/dashboard/vm/235555/')
        self.assertEqual(response.status_code, 404)

    def test_anon_vm_page(self):
        c = Client()
        response = c.get('/dashboard/vm/1/')
        self.assertRedirects(response, '/accounts/login/'
                                       '?next=/dashboard/vm/1/')

    def test_unauth_vm_page(self):
        c = Client()
        self.login(c, 'user1')
        response = c.get('/dashboard/vm/1/')
        self.assertEqual(response.status_code, 403)

    def test_operator_vm_page(self):
        c = Client()
        self.login(c, 'user2')
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u2, 'operator')
        response = c.get('/dashboard/vm/1/')
        self.assertEqual(response.status_code, 200)

    def test_user_vm_page(self):
        c = Client()
        self.login(c, 'user2')
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u2, 'user')
        response = c.get('/dashboard/vm/1/')
        self.assertEqual(response.status_code, 200)

    def test_unpermitted_password_change(self):
        c = Client()
        self.login(c, "user2")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u1, 'owner')
        password = inst.pw
        response = c.post("/dashboard/vm/1/op/password_reset/")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(password, Instance.objects.get(pk=1).pw)

    def test_unpermitted_network_add_wo_perm(self):
        c = Client()
        self.login(c, "user2")
        response = c.post("/dashboard/vm/1/op/add_interface/",
                          {'vlan': 1})
        self.assertEqual(response.status_code, 403)

    def test_unpermitted_network_add_wo_vlan_perm(self):
        c = Client()
        self.login(c, "user2")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u2, 'owner')
        interface_count = inst.interface_set.count()

        with patch.object(AddInterfaceOperation, 'async') as async:
            async.side_effect = inst.add_interface.call
            with patch.object(VmAddInterfaceView, 'get_form_kwargs',
                              autospec=True) as get_form_kwargs:
                get_form_kwargs.return_value = {'choices': Vlan.objects.all()}
                response = c.post("/dashboard/vm/1/op/add_interface/",
                                  {'vlan': 1})
        self.assertEqual(response.status_code, 302)
        assert async.called
        self.assertEqual(inst.interface_set.count(), interface_count)

    def test_permitted_network_add(self):
        c = Client()
        self.login(c, "user1")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u1, 'owner')
        vlan = Vlan.objects.get(id=1)
        vlan.set_level(self.u1, 'user')
        interface_count = inst.interface_set.count()
        with patch.object(AddInterfaceOperation, 'async') as mock_method:
            mock_method.side_effect = inst.add_interface
            response = c.post("/dashboard/vm/1/op/add_interface/",
                              {'vlan': 1})
        self.assertEqual(response.status_code, 302)
        assert mock_method.called
        self.assertEqual(inst.interface_set.count(), interface_count + 1)

    def test_permitted_network_delete(self):
        c = Client()
        self.login(c, "user1")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u1, 'owner')
        inst.add_interface(vlan=Vlan.objects.get(pk=1), user=self.us)
        inst.status = 'RUNNING'
        inst.save()

        iface_count = inst.interface_set.count()
        with patch.object(RemoveInterfaceOperation, 'async') as mock_method:
            mock_method.side_effect = inst.remove_interface
            response = c.post("/dashboard/vm/1/op/remove_interface/",
                              {'interface': 1})
        self.assertEqual(response.status_code, 302)
        assert mock_method.called
        self.assertEqual(inst.interface_set.count(), iface_count - 1)

    def test_unpermitted_network_delete(self):
        c = Client()
        self.login(c, "user1")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u1, 'user')
        inst.add_interface(vlan=Vlan.objects.get(pk=1), user=self.us)
        iface_count = inst.interface_set.count()

        with patch.object(RemoveInterfaceOperation, 'async') as mock_method:
            mock_method.side_effect = inst.remove_interface
            response = c.post("/dashboard/vm/1/op/remove_interface/",
                              {'interface': 1})
        self.assertEqual(iface_count, inst.interface_set.count())
        self.assertEqual(response.status_code, 403)

    def test_create_vm_w_unpermitted_network(self):
        c = Client()
        self.login(c, 'user2')
        response = c.post('/dashboard/vm/create/',
                          {'template': 1,
                           'cpu_priority': 1, 'cpu_count': 1,
                           'ram_size': 1000})
        self.assertEqual(response.status_code, 403)

    def test_use_unpermitted_template(self):
        c = Client()
        self.login(c, 'user1')
        Vlan.objects.get(id=1).set_level(self.u1, 'user')
        response = c.post('/dashboard/vm/create/',
                          {'template': 1,
                           'system': "bubi",
                           'cpu_priority': 1, 'cpu_count': 1,
                           'ram_size': 1000})
        self.assertEqual(response.status_code, 403)

    def test_use_permitted_template(self):
        c = Client()
        self.login(c, 'user1')
        InstanceTemplate.objects.get(id=1).set_level(self.u1, 'user')
        Vlan.objects.get(id=1).set_level(self.u1, 'user')
        with patch.object(DeployOperation, 'async') as async:
            response = c.post('/dashboard/vm/create/',
                              {'template': 1,
                               'system': "bubi",
                               'cpu_priority': 1, 'cpu_count': 1,
                               'ram_size': 1000})
        assert async.called
        self.assertEqual(response.status_code, 302)

    def test_use_permitted_template_superuser(self):
        c = Client()
        self.login(c, 'superuser')
        with patch.object(DeployOperation, 'async') as async:
            response = c.post('/dashboard/vm/create/',
                              {'template': 1,
                               'system': "bubi",
                               'cpu_priority': 1, 'cpu_count': 1,
                               'ram_size': 1000})
        assert async.called
        self.assertEqual(response.status_code, 302)

    def test_edit_unpermitted_template(self):
        c = Client()
        self.login(c, 'user1')
        InstanceTemplate.objects.get(id=1).set_level(self.u1, 'user')
        response = c.post('/dashboard/template/1/', {})
        self.assertEqual(response.status_code, 403)

    def test_edit_unpermitted_template_raw_data(self):
        c = Client()
        self.login(c, 'user1')
        tmpl = InstanceTemplate.objects.get(id=1)
        tmpl.set_level(self.u1, 'owner')
        Vlan.objects.get(id=1).set_level(self.u1, 'user')
        kwargs = tmpl.__dict__.copy()
        kwargs.update(name='t1', lease=1, disks=1, raw_data='tst1')
        response = c.post('/dashboard/template/1/', kwargs)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(InstanceTemplate.objects.get(id=1).raw_data,
                         tmpl.raw_data)

    def test_edit_permitted_template_raw_data(self):
        c = Client()
        self.login(c, 'superuser')
        kwargs = InstanceTemplate.objects.get(id=1).__dict__.copy()
        kwargs.update(name='t2', lease=1, disks=1,
                      raw_data='<devices></devices>')
        response = c.post('/dashboard/template/1/', kwargs)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(InstanceTemplate.objects.get(id=1).raw_data,
                         "<devices></devices>")

    def test_permitted_lease_delete_w_template_using_it(self):
        c = Client()
        self.login(c, 'superuser')
        leases = Lease.objects.count()
        response = c.post("/dashboard/lease/delete/1/")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(leases, Lease.objects.count())

    def test_permitted_lease_delete_w_template_not_using_it(self):
        c = Client()
        self.login(c, 'superuser')
        lease = Lease.objects.create(name="yay")
        leases = Lease.objects.count()

        response = c.post("/dashboard/lease/delete/%d/" % lease.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(leases - 1, Lease.objects.count())

    def test_unpermitted_lease_delete(self):
        c = Client()
        self.login(c, 'user1')
        leases = Lease.objects.count()
        response = c.post("/dashboard/lease/delete/1/")
        # redirect to the login page
        self.assertEqual(response.status_code, 403)
        self.assertEqual(leases, Lease.objects.count())

    def test_notification_read(self):
        c = Client()
        self.login(c, "user1")
        self.u1.profile.notify('subj', '%(var)s %(user)s',
                               {'var': 'testme'})
        assert self.u1.notification_set.get().status == 'new'
        response = c.get("/dashboard/notifications/")
        self.assertEqual(response.status_code, 200)
        assert self.u1.notification_set.get().status == 'read'

    def test_unpermitted_activity_get(self):
        c = Client()
        self.login(c, "user2")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u1, 'owner')

        response = c.get("/dashboard/vm/1/activity/")
        self.assertEqual(response.status_code, 403)

    def test_permitted_activity_get(self):
        c = Client()
        self.login(c, "user1")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u1, 'owner')

        response = c.get("/dashboard/vm/1/activity/")
        self.assertEqual(response.status_code, 200)

    def test_unpermitted_add_port_wo_config_ports_perm(self):
        c = Client()
        self.login(c, "user2")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u2, 'owner')
        vlan = Vlan.objects.get(id=1)
        vlan.set_level(self.u2, 'user')
        inst.add_interface(user=self.u2, vlan=vlan)
        host = Host.objects.get(
            interface__in=inst.interface_set.all())
        with patch.object(AddPortOperation, 'async') as mock_method:
            mock_method.side_effect = inst.add_port
            response = c.post("/dashboard/vm/1/op/add_port/", {
                'proto': 'tcp', 'host': host.pk, 'port': '1337'})
        self.assertEqual(response.status_code, 403)

    def test_unpermitted_add_port_wo_obj_levels(self):
        c = Client()
        self.login(c, "user2")
        inst = Instance.objects.get(pk=1)
        vlan = Vlan.objects.get(id=1)
        vlan.set_level(self.u2, 'user')
        inst.add_interface(user=self.u2, vlan=vlan, system=True)
        host = Host.objects.get(
            interface__in=inst.interface_set.all())
        self.u2.user_permissions.add(Permission.objects.get(
            name='Can configure port forwards.'))
        with patch.object(AddPortOperation, 'async') as mock_method:
            mock_method.side_effect = inst.add_port
            response = c.post("/dashboard/vm/1/op/add_port/", {
                'proto': 'tcp', 'host': host.pk, 'port': '1337'})
            assert not mock_method.called
        self.assertEqual(response.status_code, 403)

    def test_unpermitted_add_port_w_bad_host(self):
        c = Client()
        self.login(c, "user2")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u2, 'owner')
        self.u2.user_permissions.add(Permission.objects.get(
            name='Can configure port forwards.'))
        with patch.object(AddPortOperation, 'async') as mock_method:
            mock_method.side_effect = inst.add_port
            response = c.post("/dashboard/vm/1/op/add_port/", {
                'proto': 'tcp', 'host': '9999', 'port': '1337'})
            assert not mock_method.called
        self.assertEqual(response.status_code, 200)

    def test_permitted_add_port(self):
        c = Client()
        self.login(c, "user2")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u2, 'owner')
        vlan = Vlan.objects.get(id=1)
        vlan.set_level(self.u2, 'user')
        inst.add_interface(user=self.u2, vlan=vlan)
        host = Host.objects.get(
            interface__in=inst.interface_set.all())
        self.u2.user_permissions.add(Permission.objects.get(
            name='Can configure port forwards.'))
        port_count = len(host.list_ports())
        with patch.object(AddPortOperation, 'async') as mock_method:
            mock_method.side_effect = inst.add_port
            response = c.post("/dashboard/vm/1/op/add_port/", {
                'proto': 'tcp', 'host': host.pk, 'port': '1337'})
            assert mock_method.called
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(host.list_ports()), port_count + 1)

    def test_unpermitted_add_tag(self):
        c = Client()
        self.login(c, "user2")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u2, 'user')
        response = c.post("/dashboard/vm/1/", {'new_tag': 'test1'})
        self.assertEqual(response.status_code, 403)

    def test_permitted_add_tag(self):
        c = Client()
        self.login(c, "user2")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u2, 'owner')
        tag_count = inst.tags.count()
        response = c.post("/dashboard/vm/1/", {'new_tag': 'test2'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(inst.tags.count(), tag_count + 1)

    def test_permitted_add_tag_w_too_long_or_empty_tag(self):
        c = Client()
        self.login(c, "user2")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u2, 'owner')
        tag_count = inst.tags.count()
        response = c.post("/dashboard/vm/1/", {'new_tag': 't' * 30})
        self.assertEqual(response.status_code, 302)
        response = c.post("/dashboard/vm/1/", {'new_tag': ''})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(inst.tags.count(), tag_count)

    def test_unpermitted_remove_tag(self):
        c = Client()
        self.login(c, "user2")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u2, 'user')
        tag_count = inst.tags.count()
        response = c.post("/dashboard/vm/1/", {'to_remove': 'test1'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(inst.tags.count(), tag_count)

    def test_permitted_remove_tag(self):
        c = Client()
        self.login(c, "user2")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u2, 'owner')
        response = c.post("/dashboard/vm/1/", {'new_tag': 'test1'})
        tag_count = inst.tags.count()
        response = c.post("/dashboard/vm/1/", {'to_remove': 'test1'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(inst.tags.count(), tag_count - 1)

    def test_permitted_remove_tag_w_ajax(self):
        c = Client()
        self.login(c, "user2")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u2, 'owner')
        response = c.post("/dashboard/vm/1/", {'new_tag': 'test1'})
        tag_count = inst.tags.count()
        response = c.post("/dashboard/vm/1/", {'to_remove': 'test1'},
                          HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(inst.tags.count(), tag_count - 1)

    def test_unpermitted_set_name(self):
        c = Client()
        self.login(c, "user2")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u2, 'user')
        old_name = inst.name
        response = c.post("/dashboard/vm/1/", {'new_name': 'test1235'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Instance.objects.get(pk=1).name, old_name)

    def test_permitted_set_name(self):
        c = Client()
        self.login(c, "user2")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u2, 'owner')
        response = c.post("/dashboard/vm/1/", {'new_name': 'test1234'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Instance.objects.get(pk=1).name, 'test1234')

    def test_permitted_set_name_w_ajax(self):
        c = Client()
        self.login(c, "user2")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u2, 'owner')
        response = c.post("/dashboard/vm/1/", {'new_name': 'test123'},
                          HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Instance.objects.get(pk=1).name, 'test123')

    def test_permitted_wake_up_wrong_state(self):
        c = Client()
        self.login(c, "user2")
        with patch.object(WakeUpOperation, 'async') as mock_method, \
                patch.object(Instance.WrongStateError, 'send_message') as wro:
            inst = Instance.objects.get(pk=1)
            mock_method.side_effect = inst.wake_up
            inst.status = 'RUNNING'
            inst.set_level(self.u2, 'owner')
            c.post("/dashboard/vm/1/op/wake_up/")
            inst = Instance.objects.get(pk=1)
            self.assertEqual(inst.status, 'RUNNING')  # mocked anyway
            assert mock_method.called
            assert wro.called

    def test_permitted_wake_up(self):
        c = Client()
        self.login(c, "user2")
        with patch.object(Instance, 'select_node', return_value=None), \
                patch.object(WakeUpOperation, 'async') as new_wake_up, \
                patch.object(Instance.WrongStateError, 'send_message') as wro:
            inst = Instance.objects.get(pk=1)
            new_wake_up.side_effect = inst.wake_up
            inst._wake_up_vm = Mock()
            inst.get_remote_queue_name = Mock(return_value='test')
            inst.status = 'SUSPENDED'
            inst.set_level(self.u2, 'owner')
            with patch('dashboard.views.messages') as msg:
                response = c.post("/dashboard/vm/1/op/wake_up/")
                assert not msg.error.called
            assert inst._wake_up_vm.called
            self.assertEqual(response.status_code, 302)
            self.assertEqual(inst.status, 'RUNNING')
            assert new_wake_up.called
            assert not wro.called

    def test_unpermitted_wake_up(self):
        c = Client()
        self.login(c, "user2")
        inst = Instance.objects.get(pk=1)
        inst.status = 'SUSPENDED'
        inst.set_level(self.u2, 'user')
        response = c.post("/dashboard/vm/1/op/wake_up/")
        self.assertEqual(response.status_code, 403)

    def test_non_existing_template_get(self):
        c = Client()
        self.login(c, "superuser")
        response = c.get("/dashboard/template/111111/")
        self.assertEqual(response.status_code, 404)

    def test_permitted_customized_vm_create(self):
        c = Client()
        self.login(c, "superuser")

        instance_count = Instance.objects.all().count()
        with patch.object(DeployOperation, 'async') as async:
            response = c.post("/dashboard/vm/create/", {
                'name': 'vm',
                'amount': 2,
                'customized': 1,
                'template': 1,
                'cpu_priority': 10, 'cpu_count': 1, 'ram_size': 128,
                'network': [],
            })

        assert async.called
        self.assertEqual(response.status_code, 302)
        self.assertEqual(instance_count + 2, Instance.objects.all().count())

    def test_unpermitted_description_update(self):
        c = Client()
        self.login(c, "user1")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u2, 'owner')
        inst.set_level(self.u1, 'user')
        old_desc = inst.description
        response = c.post("/dashboard/vm/1/", {'new_description': 'test1234'})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Instance.objects.get(pk=1).description, old_desc)

    def test_permitted_description_update_w_ajax(self):
        c = Client()
        self.login(c, "user1")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u1, 'owner')
        response = c.post("/dashboard/vm/1/", {'new_description': "naonyo"},
                          HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['new_description'],
                         "naonyo")
        self.assertEqual(Instance.objects.get(pk=1).description, "naonyo")

    def test_permitted_description_update(self):
        c = Client()
        self.login(c, "user1")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u1, 'owner')
        response = c.post("/dashboard/vm/1/", {'new_description': "naonyo"})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Instance.objects.get(pk=1).description, "naonyo")


class NodeDetailTest(LoginMixin, MockCeleryMixin, TestCase):
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
        node = Node.objects.get(pk=1)
        trait, created = Trait.objects.get_or_create(name='testtrait')
        node.traits.add(trait)
        self.patcher = patch("vm.tasks.vm_tasks.get_queues", return_value={
            'x': [{'name': "devenv.vm.fast"}],
            'y': [{'name': "devenv.vm.slow"}],
            'z': [{'name': "devenv.net.fast"}],
        })
        self.patcher.start()

    def tearDown(self):
        super(NodeDetailTest, self).tearDown()
        self.u1.delete()
        self.u2.delete()
        self.us.delete()
        self.g1.delete()
        self.patcher.stop()

    def test_404_superuser_node_page(self):
        c = Client()
        self.login(c, 'superuser')
        response = c.get('/dashboard/node/25555/')
        self.assertEqual(response.status_code, 404)

    def test_200_superuser_node_page(self):
        c = Client()
        self.login(c, 'superuser')
        response = c.get('/dashboard/node/1/')
        self.assertEqual(response.status_code, 200)

    def test_302_user_node_page(self):
        c = Client()
        self.login(c, 'user1')
        response = c.get('/dashboard/node/25555/')
        self.assertEqual(response.status_code, 403)

    def test_anon_node_page(self):
        c = Client()
        response = c.get('/dashboard/node/1/')
        self.assertEqual(response.status_code, 302)

    def test_permitted_node_delete(self):
        c = Client()
        self.login(c, 'superuser')
        response = c.post('/dashboard/node/delete/1/')
        self.assertEqual(response.status_code, 302)

    def test_not_permitted_node_delete(self):
        c = Client()
        self.login(c, 'user1')
        response = c.post('/dashboard/node/delete/1/')
        self.assertEqual(response.status_code, 302)

    def test_anon_node_delete(self):
        c = Client()
        response = c.post('/dashboard/node/delete/1/')
        self.assertEqual(response.status_code, 302)

    def test_unpermitted_set_name(self):
        c = Client()
        self.login(c, "user2")
        node = Node.objects.get(pk=1)
        old_name = node.name
        response = c.post("/dashboard/node/1/", {'new_name': 'test1235'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Node.objects.get(pk=1).name, old_name)

    def test_permitted_set_name(self):
        c = Client()
        self.login(c, "superuser")
        response = c.post("/dashboard/node/1/", {'new_name': 'test1234'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Node.objects.get(pk=1).name, 'test1234')

    def test_permitted_set_name_w_ajax(self):
        c = Client()
        self.login(c, "superuser")
        response = c.post("/dashboard/node/1/", {'new_name': 'test123'},
                          HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Node.objects.get(pk=1).name, 'test123')

    def test_unpermitted_add_trait(self):
        c = Client()
        self.login(c, "user2")
        node = Node.objects.get(pk=1)
        trait_count = node.traits.count()
        response = c.post("/dashboard/node/1/add-trait/",
                          {'name': 'test1'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(Node.objects.get(pk=1).traits.all()), trait_count)

    def test_anon_add_trait(self):
        c = Client()
        node = Node.objects.get(pk=1)
        trait_count = node.traits.count()
        response = c.post("/dashboard/node/1/add-trait/",
                          {'name': 'test2'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(Node.objects.get(pk=1).traits.all()), trait_count)

    def test_permitted_add_trait(self):
        c = Client()
        self.login(c, "superuser")
        node = Node.objects.get(pk=1)
        trait_count = node.traits.count()
        response = c.post("/dashboard/node/1/add-trait/", {'name': 'test3'})
        self.assertRedirects(response, '/dashboard/node/1/')
        self.assertEqual(Node.objects.get(pk=1).traits.count(),
                         trait_count + 1)

    def test_unpermitted_remove_trait(self):
        node = Node.objects.get(pk=1)
        trait_count = node.traits.count()
        traitid = node.traits.get(name='testtrait')
        c = Client()
        self.login(c, "user2")
        response = c.post("/dashboard/node/1/", {'to_remove': traitid})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Node.objects.get(pk=1).traits.count(), trait_count)

    def test_permitted_remove_trait(self):
        node = Node.objects.get(pk=1)
        trait_count = node.traits.count()
        traitid = node.traits.get(name='testtrait').pk
        c = Client()
        self.login(c, "superuser")
        response = c.post("/dashboard/node/1/", {'to_remove': traitid})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Node.objects.get(pk=1).traits.count(),
                         trait_count - 1)

    def test_permitted_remove_trait_w_ajax(self):
        node = Node.objects.get(pk=1)
        trait_count = Node.objects.get(pk=1).traits.count()
        traitid = node.traits.get(name='testtrait').pk
        c = Client()
        self.login(c, "superuser")
        response = c.post("/dashboard/node/1/", {'to_remove': traitid},
                          HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Node.objects.get(pk=1).
                         traits.count(), trait_count - 1)

    def test_add_too_long_name_trait(self):
        c = Client()
        self.login(c, "superuser")
        node = Node.objects.get(pk=1)
        trait_count = node.traits.count()
        s = 'x' * 100
        response = c.post("/dashboard/node/1/add-trait/", {'name': s})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Node.objects.get(pk=1).traits.count(), trait_count)

    def test_anon_remove_trait(self):
        c = Client()
        node = Node.objects.get(pk=1)
        trait_count = node.traits.count()
        traitid = node.traits.get(name='testtrait').pk
        response = c.post("/dashboard/node/1/", {'to_remove': traitid})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(Node.objects.get(pk=1).traits.all()), trait_count)


class GroupCreateTest(LoginMixin, MockCeleryMixin, TestCase):
    fixtures = ['test-vm-fixture.json', 'node.json']

    def setUp(self):
        # u0 - user with creating group permissions
        self.u0 = User.objects.create(username='user0')
        self.u0.set_password('password')
        self.u0.save()
        permlist = Permission.objects.all()
        self.u0.user_permissions.add(
            filter(lambda element: 'group' in element.name and
                   'add' in element.name, permlist)[0])
        # u1 simple user without permissions
        self.u1 = User.objects.create(username='user1')
        self.u1.set_password('password')
        self.u1.save()
        self.us = User.objects.create(username='superuser', is_superuser=True)
        self.us.set_password('password')
        self.us.save()
        self.g1 = Group.objects.create(name='group1')
        self.g1.save()

    def tearDown(self):
        super(GroupCreateTest, self).tearDown()
        self.g1.delete()
        self.u0.delete()
        self.u1.delete()
        self.us.delete()

    def test_anon_group_page(self):
        c = Client()
        response = c.get('/dashboard/group/create/')
        self.assertEqual(response.status_code, 302)

    def test_superuser_group_page(self):
        c = Client()
        self.login(c, 'superuser')
        response = c.get('/dashboard/group/create/')
        self.assertEqual(response.status_code, 200)

    def test_permitted_group_page(self):
        c = Client()
        self.login(c, 'user0')
        response = c.get('/dashboard/group/create/')
        self.assertEqual(response.status_code, 200)

    def test_unpermitted_group_page(self):
        c = Client()
        self.login(c, 'user1')
        response = c.get('/dashboard/group/create/')
        self.assertEqual(response.status_code, 403)

    def test_anon_group_create(self):
        c = Client()
        groupnum = Group.objects.count()
        response = c.post('/dashboard/group/create/', {'name': 'newgroup'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Group.objects.count(), groupnum)

    def test_unpermitted_group_create(self):
        c = Client()
        groupnum = Group.objects.count()
        self.login(c, 'user1')
        response = c.post('/dashboard/group/create/', {'name': 'newgroup'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Group.objects.count(), groupnum)

    def test_permitted_group_create(self):
        c = Client()
        groupnum = Group.objects.count()
        self.login(c, 'user0')
        response = c.post('/dashboard/group/create/', {'name': 'newgroup'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Group.objects.count(), groupnum + 1)

    def test_superuser_group_create(self):
        c = Client()
        groupnum = Group.objects.count()
        self.login(c, 'superuser')
        response = c.post('/dashboard/group/create/', {'name': 'newgroup'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Group.objects.count(), groupnum + 1)

    def test_namecollision_group_create(self):
        # hint: group1 is in setUp, the tests checks creating group with the
        # same name
        c = Client()
        groupnum = Group.objects.count()
        self.login(c, 'superuser')
        response = c.post('/dashboard/group/create/', {'name': 'group1'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Group.objects.count(), groupnum)

    def test_creator_is_owner_when_group_create(self):
        # has owner rights in the group the user who created the group?
        c = Client()
        self.login(c, 'user0')
        c.post('/dashboard/group/create/', {'name': 'newgroup'})
        newgroup = Group.objects.get(name='newgroup')
        self.assertTrue(newgroup.profile.has_level(self.u0, 'owner'))


class GroupDeleteTest(LoginMixin, MockCeleryMixin, TestCase):
    fixtures = ['test-vm-fixture.json', 'node.json']

    def setUp(self):
        # u0 - user with creating group permissions
        self.u0 = User.objects.create(username='user0')
        self.u0.set_password('password')
        self.u0.save()
        permlist = Permission.objects.all()
        self.u0.user_permissions.add(
            filter(lambda element: 'group' in element.name and
                   'delete' in element.name, permlist)[0])
        # u1 simple user without permissions
        self.u1 = User.objects.create(username='user1')
        self.u1.set_password('password')
        self.u1.save()
        self.us = User.objects.create(username='superuser', is_superuser=True)
        self.us.set_password('password')
        self.us.save()
        self.g1 = Group.objects.create(name='group1')
        self.g1.profile.set_user_level(self.u0, 'owner')
        self.g1.save()

    def tearDown(self):
        super(GroupDeleteTest, self).tearDown()
        self.g1.delete()
        self.u0.delete()
        self.u1.delete()
        self.us.delete()

    def test_anon_group_page(self):
        c = Client()
        response = c.get('/dashboard/group/delete/' + str(self.g1.pk) + '/')
        self.assertEqual(response.status_code, 302)

    def test_superuser_group_page(self):
        c = Client()
        self.login(c, 'superuser')
        response = c.get('/dashboard/group/delete/' + str(self.g1.pk) + '/')
        self.assertEqual(response.status_code, 200)

    def test_permitted_group_page(self):
        c = Client()
        self.login(c, 'user0')
        with patch('dashboard.views.util.messages') as msg:
            response = c.get('/dashboard/group/delete/%d/' % self.g1.pk)
            assert not msg.error.called and not msg.warning.called
        self.assertEqual(response.status_code, 200)

    def test_unpermitted_group_page(self):
        c = Client()
        self.login(c, 'user1')
        with patch('dashboard.views.util.messages') as msg:
            response = c.get('/dashboard/group/delete/%d/' % self.g1.pk)
            assert msg.error.called or msg.warning.called
        self.assertEqual(response.status_code, 302)

    def test_anon_group_delete(self):
        c = Client()
        response = c.get('/dashboard/group/delete/%d/' % self.g1.pk)
        self.assertRedirects(
            response, '/accounts/login/?next=/dashboard/group/delete/5/',
            status_code=302)
        self.assertEqual(response.status_code, 302)

    def test_unpermitted_group_delete(self):
        c = Client()
        groupnum = Group.objects.count()
        self.login(c, 'user1')
        response = c.post('/dashboard/group/delete/' + str(self.g1.pk) + '/')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Group.objects.count(), groupnum)

    def test_permitted_group_delete(self):
        c = Client()
        groupnum = Group.objects.count()
        self.login(c, 'user0')
        response = c.post('/dashboard/group/delete/' + str(self.g1.pk) + '/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Group.objects.count(), groupnum - 1)

    def test_superuser_group_delete(self):
        c = Client()
        groupnum = Group.objects.count()
        self.login(c, 'superuser')
        response = c.post('/dashboard/group/delete/' + str(self.g1.pk) + '/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Group.objects.count(), groupnum - 1)


class GroupDetailTest(LoginMixin, MockCeleryMixin, TestCase):
    fixtures = ['test-vm-fixture.json', 'node.json']

    def setUp(self):
        Instance.get_remote_queue_name = Mock(return_value='test')
        # u0 - owner for group1
        self.u0 = User.objects.create(username='user0')
        self.u0.set_password('password')
        self.u0.save()
        self.u1 = User.objects.create(username='user1')
        self.u1.set_password('password')
        self.u1.save()
        self.u2 = User.objects.create(username='user2', is_staff=True)
        self.u2.set_password('password')
        self.u2.save()
        self.u3 = User.objects.create(username='user3')
        self.u3.set_password('password')
        self.u3.save()
        # u4 - removable user for group1
        self.u4 = User.objects.create(username='user4')
        self.u4.set_password('password')
        self.u4.save()
        self.us = User.objects.create(username='superuser', is_superuser=True)
        self.us.set_password('password')
        self.us.save()
        self.g1 = Group.objects.create(name='group1')
        self.g1.profile.set_user_level(self.u0, 'owner')
        self.g1.profile.set_user_level(self.u4, 'operator')
        self.g1.user_set.add(self.u4)
        self.g1.save()
        self.g2 = Group.objects.create(name='group2')
        self.g2.save()
        self.g3 = Group.objects.create(name='group3')
        self.g3.save()
        self.g1.profile.set_group_level(self.g3, 'operator')
        settings["default_vlangroup"] = 'public'
        VlanGroup.objects.create(name='public')

    def tearDown(self):
        super(GroupDetailTest, self).tearDown()
        self.g1.delete()
        self.g2.delete()
        self.g3.delete()
        self.u0.delete()
        self.u1.delete()
        self.u2.delete()
        self.us.delete()
        self.u3.delete()
        self.u4.delete()

    def test_404_superuser_group_page(self):
        c = Client()
        self.login(c, 'superuser')
        response = c.get('/dashboard/group/25555/')
        self.assertEqual(response.status_code, 404)

    def test_404_user_group_page(self):
        c = Client()
        self.login(c, 'user0')
        response = c.get('/dashboard/group/25555/')
        self.assertEqual(response.status_code, 404)

    def test_anon_group_page(self):
        c = Client()
        response = c.get('/dashboard/group/' + str(self.g1.pk) + '/')
        self.assertEqual(response.status_code, 302)

    def test_superuser_group_page(self):
        c = Client()
        self.login(c, 'superuser')
        response = c.get('/dashboard/group/' + str(self.g1.pk) + '/')
        self.assertEqual(response.status_code, 200)

    def test_acluser_group_page(self):
        c = Client()
        self.login(c, 'user0')
        response = c.get('/dashboard/group/' + str(self.g1.pk) + '/')
        self.assertEqual(response.status_code, 200)

    def test_acluser2_group_page(self):
        self.g1.profile.set_user_level(self.u1, 'operator')
        c = Client()
        self.login(c, 'user1')
        response = c.get('/dashboard/group/' + str(self.g1.pk) + '/')
        self.assertEqual(response.status_code, 200)

    def test_unpermitted_user_group_page(self):
        c = Client()
        self.login(c, 'user1')
        response = c.get('/dashboard/group/' + str(self.g1.pk) + '/')
        self.assertEqual(response.status_code, 403)

    def test_user_in_userlist_group_page(self):
        self.g1.user_set.add(self.u1)
        c = Client()
        self.login(c, 'user1')
        response = c.get('/dashboard/group/' + str(self.g1.pk) + '/')
        self.assertEqual(response.status_code, 403)

    def test_groupmember_group_page(self):
        self.g2.user_set.add(self.u1)
        self.g1.profile.set_group_level(self.g2, 'owner')
        c = Client()
        self.login(c, 'user1')
        response = c.get('/dashboard/group/' + str(self.g1.pk) + '/')
        self.assertEqual(response.status_code, 200)

    def test_superuser_group_delete(self):
        num_of_groups = Group.objects.count()
        c = Client()
        self.login(c, 'superuser')
        response = c.post('/dashboard/group/delete/' + str(self.g1.pk) + '/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Group.objects.count(), num_of_groups - 1)

    def test_unpermitted_group_delete(self):
        num_of_groups = Group.objects.count()
        c = Client()
        self.login(c, 'user3')
        response = c.post('/dashboard/group/delete/' + str(self.g1.pk) + '/')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Group.objects.count(), num_of_groups)

    def test_acl_group_delete(self):
        num_of_groups = Group.objects.count()
        c = Client()
        self.login(c, 'user0')
        response = c.post('/dashboard/group/delete/' + str(self.g1.pk) + '/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Group.objects.count(), num_of_groups - 1)

    def test_anon_group_delete(self):
        num_of_groups = Group.objects.count()
        c = Client()
        response = c.post('/dashboard/group/delete/' + str(self.g1.pk) + '/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Group.objects.count(), num_of_groups)

    # add to group

    def test_anon_add_user_to_group(self):
        c = Client()
        user_in_group = self.g1.user_set.count()
        response = c.post('/dashboard/group/' +
                          str(self.g1.pk) + '/', {'new_member': 'user3'})
        self.assertEqual(user_in_group,
                         self.g1.user_set.count())
        self.assertEqual(response.status_code, 302)

    def test_unpermitted_add_user_to_group(self):
        c = Client()
        self.login(c, 'user3')
        user_in_group = self.g1.user_set.count()
        response = c.post('/dashboard/group/' +
                          str(self.g1.pk) + '/', {'new_member': 'user3'})
        self.assertEqual(user_in_group, self.g1.user_set.count())
        self.assertEqual(response.status_code, 403)

    def test_superuser_add_user_to_group(self):
        c = Client()
        self.login(c, 'superuser')
        user_in_group = self.g1.user_set.count()
        response = c.post('/dashboard/group/' +
                          str(self.g1.pk) + '/', {'new_member': 'user3'})
        self.assertEqual(user_in_group + 1, self.g1.user_set.count())
        self.assertEqual(response.status_code, 302)

    def test_permitted_add_user_to_group(self):
        c = Client()
        self.login(c, 'user0')
        user_in_group = self.g1.user_set.count()
        response = c.post('/dashboard/group/' +
                          str(self.g1.pk) + '/', {'new_member': 'user3'})
        self.assertEqual(user_in_group + 1, self.g1.user_set.count())
        self.assertEqual(response.status_code, 302)

    def test_permitted_add_multipleuser_to_group(self):
        c = Client()
        self.login(c, 'user0')
        user_in_group = self.g1.user_set.count()
        response = c.post('/dashboard/group/' +
                          str(self.g1.pk) + '/',
                          {'new_members': 'user1\r\nuser2'})
        self.assertEqual(user_in_group + 2, self.g1.user_set.count())
        self.assertEqual(response.status_code, 302)

    def test_add_multipleuser_skip_badname_to_group(self):
        c = Client()
        self.login(c, 'user0')
        user_in_group = self.g1.user_set.count()
        response = c.post('/dashboard/group/' +
                          str(self.g1.pk) + '/',
                          {'new_members': 'user1\r\nnoname\r\nuser2'})
        self.assertEqual(user_in_group + 2, self.g1.user_set.count())
        self.assertEqual(response.status_code, 302)

    def test_unpermitted_add_multipleuser_to_group(self):
        c = Client()
        self.login(c, 'user3')
        user_in_group = self.g1.user_set.count()
        response = c.post('/dashboard/group/' +
                          str(self.g1.pk) + '/',
                          {'new_members': 'user1\r\nuser2'})
        self.assertEqual(user_in_group, self.g1.user_set.count())
        self.assertEqual(response.status_code, 403)

    def test_anon_add_multipleuser_to_group(self):
        c = Client()
        user_in_group = self.g1.user_set.count()
        response = c.post('/dashboard/group/' +
                          str(self.g1.pk) + '/',
                          {'new_members': 'user1\r\nuser2'})
        self.assertEqual(user_in_group, self.g1.user_set.count())
        self.assertEqual(response.status_code, 302)

    def test_anon_add_acluser_to_group(self):
        c = Client()
        gp = self.g1.profile
        acl_users = len(gp.get_users_with_level())
        response = c.post('/dashboard/group/' +
                          str(gp.pk) + '/acl/',
                          {'name': 'user3', 'level': 'owner'})
        self.assertEqual(acl_users, len(gp.get_users_with_level()))
        self.assertEqual(response.status_code, 302)

    def test_unpermitted_add_acluser_to_group(self):
        c = Client()
        self.login(c, 'user3')
        gp = self.g1.profile
        acl_users = len(gp.get_users_with_level())
        response = c.post('/dashboard/group/' +
                          str(gp.pk) + '/acl/',
                          {'name': 'user3', 'level': 'owner'})
        self.assertEqual(acl_users, len(gp.get_users_with_level()))
        self.assertEqual(response.status_code, 302)

    def test_superuser_add_acluser_to_group(self):
        c = Client()
        gp = self.g1.profile
        self.login(c, 'superuser')
        acl_users = len(gp.get_users_with_level())
        response = c.post('/dashboard/group/' +
                          str(gp.pk) + '/acl/',
                          {'name': 'user3', 'level': 'owner'})
        self.assertEqual(acl_users + 1, len(gp.get_users_with_level()))
        self.assertEqual(response.status_code, 302)

    def test_permitted_add_acluser_to_group(self):
        c = Client()
        gp = self.g1.profile
        self.login(c, 'user0')
        acl_users = len(gp.get_users_with_level())
        response = c.post('/dashboard/group/' +
                          str(gp.pk) + '/acl/',
                          {'name': 'user3', 'level': 'owner'})
        self.assertEqual(acl_users + 1, len(gp.get_users_with_level()))
        self.assertEqual(response.status_code, 302)

    def test_anon_add_aclgroup_to_group(self):
        c = Client()
        gp = self.g1.profile
        acl_groups = len(gp.get_groups_with_level())
        response = c.post('/dashboard/group/' +
                          str(gp.pk) + '/acl/',
                          {'name': 'group2', 'level': 'owner'})
        self.assertEqual(acl_groups, len(gp.get_groups_with_level()))
        self.assertEqual(response.status_code, 302)

    def test_unpermitted_add_aclgroup_to_group(self):
        c = Client()
        gp = self.g1.profile
        self.login(c, 'user3')
        acl_groups = len(gp.get_groups_with_level())
        response = c.post('/dashboard/group/' +
                          str(gp.pk) + '/acl/',
                          {'name': 'group2', 'level': 'owner'})
        self.assertEqual(acl_groups, len(gp.get_groups_with_level()))
        self.assertEqual(response.status_code, 302)

    def test_superuser_add_aclgroup_to_group(self):
        c = Client()
        gp = self.g1.profile
        self.login(c, 'superuser')
        acl_groups = len(gp.get_groups_with_level())
        response = c.post('/dashboard/group/' +
                          str(gp.pk) + '/acl/',
                          {'name': 'group2', 'level': 'owner'})
        self.assertEqual(acl_groups + 1, len(gp.get_groups_with_level()))
        self.assertEqual(response.status_code, 302)

    def test_permitted_add_aclgroup_to_group(self):
        c = Client()
        gp = self.g1.profile
        self.login(c, 'user0')
        acl_groups = len(gp.get_groups_with_level())
        response = c.post('/dashboard/group/' +
                          str(gp.pk) + '/acl/',
                          {'name': 'group2', 'level': 'owner'})
        self.assertEqual(acl_groups + 1, len(gp.get_groups_with_level()))
        self.assertEqual(response.status_code, 302)

    # remove from group

    def test_anon_remove_user_from_group(self):
        c = Client()
        user_in_group = self.g1.user_set.count()
        response = c.post('/dashboard/group/' + str(self.g1.pk) +
                          '/remove/user/' + str(self.u4.pk) + '/')
        self.assertEqual(user_in_group,
                         self.g1.user_set.count())
        self.assertEqual(response.status_code, 302)

    def test_unpermitted_remove_user_from_group(self):
        c = Client()
        self.login(c, 'user3')
        user_in_group = self.g1.user_set.count()
        response = c.post('/dashboard/group/' + str(self.g1.pk) +
                          '/remove/user/' + str(self.u4.pk) + '/')
        self.assertEqual(user_in_group, self.g1.user_set.count())
        self.assertEqual(response.status_code, 403)

    def test_superuser_remove_user_from_group(self):
        c = Client()
        self.login(c, 'superuser')
        user_in_group = self.g1.user_set.count()
        response = c.post('/dashboard/group/' + str(self.g1.pk) +
                          '/remove/user/' + str(self.u4.pk) + '/')
        self.assertEqual(user_in_group - 1, self.g1.user_set.count())
        self.assertEqual(response.status_code, 302)

    def test_permitted_remove_user_from_group(self):
        c = Client()
        self.login(c, 'user0')
        user_in_group = self.g1.user_set.count()
        response = c.post('/dashboard/group/' + str(self.g1.pk) +
                          '/remove/user/' + str(self.u4.pk) + '/')
        self.assertEqual(user_in_group - 1, self.g1.user_set.count())
        self.assertEqual(response.status_code, 302)

    def test_unpermitted_user_add_wo_group_perm(self):
        user_count = self.g1.user_set.count()
        c = Client()
        self.login(c, 'user1')
        self.u1.user_permissions.add(Permission.objects.get(
            name='Can add user'))
        response = c.post('/dashboard/profile/create/',
                          {'username': 'userx1',
                           'groups': self.g1.pk,
                           'password1': 'test123',
                           'password2': 'test123'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(user_count, self.g1.user_set.count())

    def test_permitted_user_add_wo_can_add_user_perm(self):
        user_count = self.g1.user_set.count()
        c = Client()
        self.login(c, 'user0')
        response = c.post('/dashboard/profile/create/',
                          {'username': 'userx2',
                           'groups': self.g1.pk,
                           'password1': 'test123',
                           'password2': 'test123'})
        self.assertRedirects(
            response,
            '/accounts/login/?next=/dashboard/profile/create/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(user_count, self.g1.user_set.count())

    def test_permitted_user_add(self):
        user_count = self.g1.user_set.count()
        self.u0.user_permissions.add(Permission.objects.get(
            name='Can add user'))
        c = Client()
        self.login(c, 'user0')
        response = c.post('/dashboard/profile/create/',
                          {'username': 'userx2',
                           'groups': self.g1.pk,
                           'password1': 'test123',
                           'password2': 'test123'})
        self.assertRedirects(response, '/dashboard/profile/userx2/')
        self.assertEqual(user_count + 1, self.g1.user_set.count())
        self.assertEqual(response.status_code, 302)


class GroupListTest(LoginMixin, MockCeleryMixin, TestCase):
    fixtures = ['test-vm-fixture.json', 'node.json']

    def setUp(self):
        self.u1 = User.objects.create(username='user1')
        self.u1.set_password('password')
        self.u1.save()
        permlist = Permission.objects.all()
        self.u1.user_permissions.add(
            filter(lambda element: 'group' in element.name and
                   'add' in element.name, permlist)[0])
        self.u2 = User.objects.create(username='user2')
        self.u2.set_password('password')
        self.u2.save()
        self.g1 = Group.objects.create(name='group1')
        self.g1.profile.set_user_level(self.u1, 'owner')
        self.g1.save()
        self.g2 = Group.objects.create(name='group2')
        self.g2.profile.set_user_level(self.u1, 'owner')
        self.g2.save()
        self.g3 = Group.objects.create(name='group3')
        self.g3.profile.set_user_level(self.u1, 'owner')
        self.g3.save()

    def test_anon_filter(self):
        c = Client()
        response = c.get('/dashboard/group/list/?s="3"')
        self.assertEqual(response.status_code, 302)

    def test_permitteduser_filter(self):
        c = Client()
        self.login(c, 'user1')
        response = c.get('/dashboard/group/list/?s="3"')
        self.assertEqual(response.status_code, 200)

    def tearDown(self):
        super(GroupListTest, self).tearDown()
        self.u1.delete()
        self.u2.delete()
        self.g1.delete()
        self.g2.delete()


class VmDetailVncTest(LoginMixin, MockCeleryMixin, TestCase):
    fixtures = ['test-vm-fixture.json', 'node.json']

    def setUp(self):
        self.u1 = User.objects.create(username='user1')
        self.u1.set_password('password')
        self.u1.save()

    def test_permitted_vm_console(self):
        c = Client()
        self.login(c, 'user1')
        inst = Instance.objects.get(pk=1)
        inst.node = Node.objects.all()[0]
        inst.save()
        inst.set_level(self.u1, 'operator')
        self.u1.user_permissions.add(Permission.objects.get(
            codename='access_console'))
        response = c.get('/dashboard/vm/1/vnctoken/')
        self.assertEqual(response.status_code, 200)

    def test_not_permitted_vm_console(self):
        c = Client()
        self.login(c, 'user1')
        inst = Instance.objects.get(pk=1)
        inst.node = Node.objects.all()[0]
        inst.save()
        inst.set_level(self.u1, 'user')
        self.u1.user_permissions.add(Permission.objects.get(
            codename='access_console'))
        response = c.get('/dashboard/vm/1/vnctoken/')
        self.assertEqual(response.status_code, 403)


class TransferOwnershipViewTest(LoginMixin, MockCeleryMixin, TestCase):
    fixtures = ['test-vm-fixture.json']

    def setUp(self):
        self.u1 = User.objects.create(username='user1')
        self.u1.set_password('password')
        self.u1.save()
        Profile.objects.create(user=self.u1)
        self.u2 = User.objects.create(username='user2', is_staff=True)
        self.u2.set_password('password')
        self.u2.save()
        Profile.objects.create(user=self.u2)
        self.us = User.objects.create(username='superuser', is_superuser=True)
        self.us.set_password('password')
        self.us.save()
        Profile.objects.create(user=self.us)
        inst = Instance.objects.get(pk=1)
        inst.owner = self.u1
        inst.save()

    def test_non_owner_offer(self):
        c2 = self.u2.notification_set.count()
        c = Client()
        self.login(c, 'user2')
        response = c.post('/dashboard/vm/1/tx/', {'name': 'userx'})
        assert response.status_code == 403
        self.assertEqual(self.u2.notification_set.count(), c2)

    def test_owned_offer(self):
        c2 = self.u2.notification_set.count()
        c = Client()
        self.login(c, 'user1')
        response = c.get('/dashboard/vm/1/tx/')
        assert response.status_code == 200
        response = c.post('/dashboard/vm/1/tx/', {'name': 'user2'})
        self.assertEqual(self.u2.notification_set.count(), c2 + 1)


class IndexViewTest(LoginMixin, MockCeleryMixin, TestCase):
    fixtures = ['test-vm-fixture.json', 'node.json']

    def setUp(self):
        self.u1 = User.objects.create(username='user1')
        self.u1.set_password('password')
        self.u1.save()
        self.us = User.objects.create(username='superuser', is_superuser=True)
        self.us.set_password('password')
        self.us.save()

    def test_context_variables_as_user(self):
        c = Client()
        self.login(c, 'user1')
        response = c.get("/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse("nodes" in response.context)

    def test_context_variables_as_superuser(self):
        c = Client()
        self.login(c, 'superuser')
        response = c.get("/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue("nodes" in response.context)

    def test_context_processor_notifications(self):
        c = Client()
        self.login(c, "user1")

        response = c.get("/dashboard/")
        self.assertEqual(response.context['NEW_NOTIFICATIONS_COUNT'], 0)

        self.u1.profile.notify("urgent", "%(var)s %(user)s", )
        response = c.get("/dashboard/")
        self.assertEqual(response.context['NEW_NOTIFICATIONS_COUNT'], 1)


class ProfileViewTest(LoginMixin, TestCase):

    def setUp(self):
        self.u1 = User.objects.create(username='user1')
        self.u1.set_password('password')
        self.u1.save()
        self.p1 = Profile.objects.create(user=self.u1)
        self.p1.save()

    def test_permitted_language_change(self):
        c = Client()
        self.login(c, "user1")
        old_language_cookie_value = c.cookies['django_language'].value
        old_language_db_value = self.u1.profile.preferred_language
        response = c.post("/dashboard/profile/", {
            'preferred_language': "hu",
        })

        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(old_language_cookie_value,
                            c.cookies['django_language'].value)
        self.assertNotEqual(old_language_db_value,
                            User.objects.get(
                                username="user1").profile.preferred_language)

    def test_permitted_valid_password_change(self):
        c = Client()
        self.login(c, "user1")

        c.post("/dashboard/profile/", {
            'old_password': "password",
            'new_password1': "asd",
            'new_password2': "asd",
        })

        self.assertIsNone(authenticate(username="user1", password="password"))
        self.assertIsNotNone(authenticate(username="user1", password="asd"))

    def test_permitted_invalid_password_changes(self):
        c = Client()
        self.login(c, "user1")

        # wrong current password
        c.post("/dashboard/profile/", {
            'old_password': "password1",
            'new_password1': "asd",
            'new_password2': "asd",
        })

        self.assertIsNotNone(authenticate(username="user1",
                                          password="password"))
        self.assertIsNone(authenticate(username="user1", password="asd"))

        # wrong pw confirmation
        c.post("/dashboard/profile/", {
            'old_password': "password",
            'new_password1': "asd",
            'new_password2': "asd1",
        })

        self.assertIsNotNone(authenticate(username="user1",
                                          password="password"))
        self.assertIsNone(authenticate(username="user1", password="asd"))


class AclViewTest(LoginMixin, MockCeleryMixin, TestCase):
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
        self.ut = User.objects.get(username="test")
        self.g1 = Group.objects.create(name='group1')
        self.g1.user_set.add(self.u1)
        self.g1.user_set.add(self.u2)
        self.g1.save()
        settings["default_vlangroup"] = 'public'
        VlanGroup.objects.create(name='public')

    def tearDown(self):
        super(AclViewTest, self).tearDown()
        self.u1.delete()
        self.u2.delete()
        self.us.delete()
        self.g1.delete()

    def test_permitted_instance_access_revoke(self):
        c = Client()
        # this is from the fixtures
        self.login(c, "test", "test")
        inst = Instance.objects.get(id=1)
        inst.set_level(self.u1, "user")

        resp = c.post("/dashboard/vm/1/acl/", {
            'remove-u-%d' % self.u1.pk: "",
            'name': "",
            'level': "",
        })
        self.assertFalse((self.u1, "user") in inst.get_users_with_level())
        self.assertEqual(resp.status_code, 302)

    def test_unpermitted_instance_access_revoke(self):
        c = Client()
        self.login(c, self.u2)
        inst = Instance.objects.get(id=1)
        inst.set_level(self.u1, "user")

        resp = c.post("/dashboard/vm/1/acl/", {
            'remove-u-%d' % self.u1.pk: "",
            'name': "",
            'level': "",
        })
        self.assertTrue((self.u1, "user") in inst.get_users_with_level())
        self.assertEqual(resp.status_code, 302)

    def test_instance_original_owner_access_revoke(self):
        c = Client()
        self.login(c, self.u1)
        inst = Instance.objects.get(id=1)
        inst.set_level(self.u1, "owner")
        inst.set_level(self.ut, "owner")
        resp = c.post("/dashboard/vm/1/acl/", {
            'remove-u-%d' % self.ut.pk: "",
            'name': "",
            'level': "",
        })
        self.assertEqual(self.ut, Instance.objects.get(id=1).owner)
        self.assertTrue((self.ut, "owner") in inst.get_users_with_level())
        self.assertEqual(resp.status_code, 302)

    def test_permitted_template_access_revoke(self):
        c = Client()
        # this is from the fixtures
        self.login(c, "test", "test")
        tmpl = InstanceTemplate.objects.get(id=1)
        tmpl.set_level(self.u1, "user")

        resp = c.post("/dashboard/template/1/acl/", {
            'remove-u-%d' % self.u1.pk: "",
            'name': "",
            'level': "",
        })
        self.assertFalse((self.u1, "user") in tmpl.get_users_with_level())
        self.assertEqual(resp.status_code, 302)

    def test_unpermitted_template_access_revoke(self):
        c = Client()
        self.login(c, self.u2)
        tmpl = InstanceTemplate.objects.get(id=1)
        tmpl.set_level(self.u1, "user")

        resp = c.post("/dashboard/template/1/acl/", {
            'remove-u-%d' % self.u1.pk: "",
            'name': "",
            'level': "",
        })
        self.assertTrue((self.u1, "user") in tmpl.get_users_with_level())
        self.assertEqual(resp.status_code, 302)

    def test_template_original_owner_access_revoke(self):
        c = Client()
        self.login(c, self.u1)
        tmpl = InstanceTemplate.objects.get(id=1)
        tmpl.set_level(self.u1, "owner")
        tmpl.set_level(self.ut, "owner")
        resp = c.post("/dashboard/template/1/acl/", {
            'remove-u-%d' % self.ut.pk: "",
            'name': "",
            'level': "",
        })
        self.assertEqual(self.ut, InstanceTemplate.objects.get(id=1).owner)
        self.assertTrue((self.ut, "owner") in tmpl.get_users_with_level())
        self.assertEqual(resp.status_code, 302)


class VmListTest(LoginMixin, MockCeleryMixin, TestCase):
    fixtures = ['test-vm-fixture.json', 'node.json']

    def setUp(self):
        Instance.get_remote_queue_name = Mock(return_value='test')
        self.u1 = User.objects.create(username='user1')
        self.u1.set_password('password')
        self.u1.save()

    def tearDown(self):
        super(VmListTest, self).tearDown()
        self.u1.delete()

    def test_filter_w_invalid_input(self):
        c = Client()
        self.login(c, self.u1)

        resp = c.get("/dashboard/vm/list/", {
            's': "A:B:C:D:"
        })
        self.assertEqual(200, resp.status_code)


class SshKeyTest(LoginMixin, TestCase):
    def setUp(self):
        self.u1 = User.objects.create(username='user1')
        self.u1.set_password('password')
        self.u1.profile = Profile()
        self.u1.save()
        self.u2 = User.objects.create(username='user2')
        self.u2.set_password('password')
        self.u2.profile = Profile()
        self.u2.save()
        self.valid_key = (
            "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAYQDGqQy86fpVL3fAPE9ExTSvg4"
            "Me7bpzH4azerTwWl8u9KKbhYe8XnC+cpvzbRxinFE9SqgQtKJzuxE0f/hHsNCQ"
            "t3zDLHsqfFUdFQzkImXJ+duUKGyHKIsx6Os0j6nl+3c= asd")
        self.k1 = UserKey(key=self.valid_key, user=self.u1)
        self.k1.save()

    def tearDown(self):
        super(SshKeyTest, self).tearDown()
        self.k1.delete()
        self.u1.delete()

    def test_permitted_edit(self):
        c = Client()
        self.login(c, self.u1)

        resp = c.post("/dashboard/sshkey/1/",
                      {'key': self.valid_key})
        self.assertEqual(UserKey.objects.get(id=1).user, self.u1)
        self.assertEqual(200, resp.status_code)

    def test_unpermitted_edit(self):
        c = Client()
        self.login(c, self.u2)

        resp = c.post("/dashboard/sshkey/1/",
                      {'key': self.valid_key})
        self.assertEqual(UserKey.objects.get(id=1).user, self.u1)
        self.assertEqual(403, resp.status_code)

    def test_permitted_add(self):
        c = Client()
        self.login(c, self.u1)

        resp = c.post("/dashboard/sshkey/create/",
                      {'name': 'asd', 'key': self.valid_key})
        self.assertEqual(UserKey.objects.get(id=2).user, self.u1)
        self.assertEqual(302, resp.status_code)

    def test_permitted_delete(self):
        c = Client()
        self.login(c, self.u1)

        resp = c.post("/dashboard/sshkey/delete/1/")
        self.assertEqual(302, resp.status_code)

    def test_unpermitted_delete(self):
        c = Client()
        self.login(c, self.u2)

        resp = c.post("/dashboard/sshkey/delete/1/")
        self.assertEqual(403, resp.status_code)
