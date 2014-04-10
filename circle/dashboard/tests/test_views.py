from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User, Group
from django.core.exceptions import SuspiciousOperation
from django.core.urlresolvers import reverse
from django.contrib.auth.models import Permission

from vm.models import Instance, InstanceTemplate, Lease, Node
from ..models import Profile
from ..views import VmRenewView
from storage.models import Disk
from firewall.models import Vlan, Host, VlanGroup
from mock import Mock, patch

import django.conf
settings = django.conf.settings.FIREWALL_SETTINGS


class LoginMixin(object):
    def login(self, client, username, password='password'):
        response = client.post('/accounts/login/', {'username': username,
                                                    'password': password})
        self.assertNotEqual(response.status_code, 403)


class VmDetailTest(LoginMixin, TestCase):
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

    def test_permitted_vm_delete(self):
        c = Client()
        self.login(c, 'user2')
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u2, 'owner')
        response = c.post('/dashboard/vm/delete/1/')
        self.assertEqual(response.status_code, 302)

    def test_not_permitted_vm_delete(self):
        c = Client()
        self.login(c, 'user2')
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u2, 'operator')
        response = c.post('/dashboard/vm/delete/1/')
        self.assertEqual(response.status_code, 403)

    def test_unpermitted_vm_delete(self):
        c = Client()
        self.login(c, 'user1')
        response = c.post('/dashboard/vm/delete/1/')
        self.assertEqual(response.status_code, 403)

    def test_unpermitted_vm_mass_delete(self):
        c = Client()
        self.login(c, 'user1')
        response = c.post('/dashboard/vm/mass-delete/', {'vms': [1]})
        self.assertEqual(response.status_code, 403)

    def test_permitted_vm_mass_delete(self):
        c = Client()
        self.login(c, 'user2')
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u2, 'owner')
        response = c.post('/dashboard/vm/mass-delete/', {'vms': [1]})
        self.assertEqual(response.status_code, 302)

    def test_permitted_password_change(self):
        c = Client()
        self.login(c, "user2")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u2, 'owner')
        inst.node = Node.objects.all()[0]
        inst.save()
        password = inst.pw
        response = c.post("/dashboard/vm/1/", {'change_password': True})
        self.assertTrue(Instance.get_remote_queue_name.called)
        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(password, Instance.objects.get(pk=1).pw)

    def test_unpermitted_password_change(self):
        c = Client()
        self.login(c, "user2")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u1, 'owner')
        password = inst.pw
        response = c.post("/dashboard/vm/1/", {'change_password': True})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(password, Instance.objects.get(pk=1).pw)

    def test_unpermitted_network_add_wo_perm(self):
        c = Client()
        self.login(c, "user2")
        response = c.post("/dashboard/vm/1/", {'new_network_vlan': 1})
        self.assertEqual(response.status_code, 403)

    def test_unpermitted_network_add_wo_vlan_perm(self):
        c = Client()
        self.login(c, "user2")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u2, 'owner')
        response = c.post("/dashboard/vm/1/", {'new_network_vlan': 1})
        self.assertEqual(response.status_code, 403)

    def test_permitted_network_add(self):
        c = Client()
        self.login(c, "user1")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u1, 'owner')
        vlan = Vlan.objects.get(id=1)
        vlan.set_level(self.u1, 'user')
        interface_count = inst.interface_set.count()
        response = c.post("/dashboard/vm/1/",
                          {'new_network_vlan': 1})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(inst.interface_set.count(), interface_count + 1)

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
        Disk.objects.get(id=1).set_level(self.u1, 'user')
        Vlan.objects.get(id=1).set_level(self.u1, 'user')
        response = c.post('/dashboard/vm/create/',
                          {'template': 1,
                           'cpu_priority': 1, 'cpu_count': 1,
                           'ram_size': 1000})
        self.assertEqual(response.status_code, 403)

    def test_use_permitted_template(self):
        c = Client()
        self.login(c, 'user1')
        Disk.objects.get(id=1).set_level(self.u1, 'user')
        InstanceTemplate.objects.get(id=1).set_level(self.u1, 'user')
        Vlan.objects.get(id=1).set_level(self.u1, 'user')
        response = c.post('/dashboard/vm/create/',
                          {'template': 1,
                           'cpu_priority': 1, 'cpu_count': 1,
                           'ram_size': 1000})
        self.assertEqual(response.status_code, 302)

    def test_use_permitted_template_superuser(self):
        c = Client()
        self.login(c, 'superuser')
        response = c.post('/dashboard/vm/create/',
                          {'template': 1,
                           'cpu_priority': 1, 'cpu_count': 1,
                           'ram_size': 1000})
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
        tmpl.disks.get().set_level(self.u1, 'owner')
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
        kwargs.update(name='t2', lease=1, disks=1, raw_data='tst2')
        response = c.post('/dashboard/template/1/', kwargs)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(InstanceTemplate.objects.get(id=1).raw_data, 'tst2')

    def test_permitted_lease_delete(self):
        c = Client()
        self.login(c, 'superuser')
        leases = Lease.objects.count()
        response = c.post("/dashboard/lease/delete/1/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(leases - 1, Lease.objects.count())

    def test_unpermitted_lease_delete(self):
        c = Client()
        self.login(c, 'user1')
        leases = Lease.objects.count()
        response = c.post("/dashboard/lease/delete/1/")
        # redirect to the login page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(leases, Lease.objects.count())

    def test_unpermitted_vm_disk_add(self):
        c = Client()
        self.login(c, "user2")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u1, 'owner')
        disks = inst.disks.count()
        response = c.post("/dashboard/disk/add/", {
            'disk-name': "a",
            'disk-size': 1,
            'disk-is_template': 0,
            'disk-object_pk': 1,
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(disks, inst.disks.count())

    def test_permitted_vm_disk_add(self):
        c = Client()
        self.login(c, "user1")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u1, 'owner')
        # disks = inst.disks.count()
        response = c.post("/dashboard/disk/add/", {
            'disk-name': "a",
            'disk-size': 1,
            'disk-is_template': 0,
            'disk-object_pk': 1,
        })
        self.assertEqual(response.status_code, 302)
        # mancelery is needed TODO
        # self.assertEqual(disks + 1, inst.disks.count())

    def test_notification_read(self):
        c = Client()
        self.login(c, "user1")
        self.u1.profile.notify('subj', 'dashboard/test_message.txt',
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
        response = c.post("/dashboard/vm/1/", {'port': True,
                                               'proto': 'tcp',
                                               'port': '1337'})
        self.assertEqual(response.status_code, 403)

    def test_unpermitted_add_port_wo_obj_levels(self):
        c = Client()
        self.login(c, "user2")
        self.u2.user_permissions.add(Permission.objects.get(
            name='Can configure port forwards.'))
        response = c.post("/dashboard/vm/1/", {'port': True,
                                               'proto': 'tcp',
                                               'port': '1337'})
        self.assertEqual(response.status_code, 403)

    def test_unpermitted_add_port_w_bad_host(self):
        c = Client()
        self.login(c, "user2")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u2, 'owner')
        self.u2.user_permissions.add(Permission.objects.get(
            name='Can configure port forwards.'))
        response = c.post("/dashboard/vm/1/", {'proto': 'tcp',
                                               'host_pk': '9999',
                                               'port': '1337'})
        self.assertEqual(response.status_code, 403)

    def test_permitted_add_port_w_unhandled_exception(self):
        c = Client()
        self.login(c, "user2")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u2, 'owner')
        vlan = Vlan.objects.get(id=1)
        vlan.set_level(self.u2, 'user')
        response = c.post("/dashboard/vm/1/",
                          {'new_network_vlan': 1})
        host = Host.objects.get(
            interface__in=inst.interface_set.all())
        self.u2.user_permissions.add(Permission.objects.get(
            name='Can configure port forwards.'))
        port_count = len(host.list_ports())
        response = c.post("/dashboard/vm/1/", {'proto': 'tcp',
                                               'host_pk': host.pk,
                                               'port': 'invalid_port'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(host.list_ports()), port_count)

    def test_permitted_add_port(self):
        c = Client()
        self.login(c, "user2")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u2, 'owner')
        vlan = Vlan.objects.get(id=1)
        vlan.set_level(self.u2, 'user')
        response = c.post("/dashboard/vm/1/",
                          {'new_network_vlan': 1})
        host = Host.objects.get(
            interface__in=inst.interface_set.all())
        self.u2.user_permissions.add(Permission.objects.get(
            name='Can configure port forwards.'))
        port_count = len(host.list_ports())
        response = c.post("/dashboard/vm/1/", {'proto': 'tcp',
                                               'host_pk': host.pk,
                                               'port': '1337'})
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
        with patch.object(Instance, 'wake_up_async') as mock_method:
            inst = Instance.objects.get(pk=1)
            mock_method.side_effect = inst.wake_up
            inst.manual_state_change('RUNNING')
            inst.set_level(self.u2, 'owner')
            self.assertRaises(inst.WrongStateError, c.post,
                              "/dashboard/vm/1/", {'wake_up': True})
            self.assertEqual(inst.status, 'RUNNING')
            assert mock_method.called

    def test_permitted_wake_up(self):
        c = Client()
        self.login(c, "user2")
        with patch.object(Instance, 'select_node', return_value=None):
            with patch.object(Instance, 'wake_up_async') as new_wake_up:
                with patch('vm.tasks.vm_tasks.wake_up.apply_async') as wuaa:
                    inst = Instance.objects.get(pk=1)
                    new_wake_up.side_effect = inst.wake_up
                    inst.get_remote_queue_name = Mock(return_value='test')
                    inst.manual_state_change('SUSPENDED')
                    inst.set_level(self.u2, 'owner')
                    response = c.post("/dashboard/vm/1/", {'wake_up': True})
                    self.assertEqual(response.status_code, 302)
                    self.assertEqual(inst.status, 'RUNNING')
                    assert new_wake_up.called
                    assert wuaa.called

    def test_unpermitted_wake_up(self):
        c = Client()
        self.login(c, "user2")
        inst = Instance.objects.get(pk=1)
        inst.manual_state_change('SUSPENDED')
        inst.set_level(self.u2, 'user')
        response = c.post("/dashboard/vm/1/", {'wake_up': True})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(inst.status, 'SUSPENDED')


class GroupDetailTest(LoginMixin, TestCase):
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
                          str(self.g1.pk) + '/', {'list-new-name': 'user3'})
        self.assertEqual(user_in_group,
                         self.g1.user_set.count())
        self.assertEqual(response.status_code, 302)

    def test_unpermitted_add_user_to_group(self):
        c = Client()
        self.login(c, 'user3')
        user_in_group = self.g1.user_set.count()
        response = c.post('/dashboard/group/' +
                          str(self.g1.pk) + '/', {'list-new-name': 'user3'})
        self.assertEqual(user_in_group, self.g1.user_set.count())
        self.assertEqual(response.status_code, 403)

    def test_superuser_add_user_to_group(self):
        c = Client()
        self.login(c, 'superuser')
        user_in_group = self.g1.user_set.count()
        response = c.post('/dashboard/group/' +
                          str(self.g1.pk) + '/', {'list-new-name': 'user3'})
        self.assertEqual(user_in_group + 1, self.g1.user_set.count())
        self.assertEqual(response.status_code, 302)

    def test_permitted_add_user_to_group(self):
        c = Client()
        self.login(c, 'user0')
        user_in_group = self.g1.user_set.count()
        response = c.post('/dashboard/group/' +
                          str(self.g1.pk) + '/', {'list-new-name': 'user3'})
        self.assertEqual(user_in_group + 1, self.g1.user_set.count())
        self.assertEqual(response.status_code, 302)

    def test_permitted_add_multipleuser_to_group(self):
        c = Client()
        self.login(c, 'user0')
        user_in_group = self.g1.user_set.count()
        response = c.post('/dashboard/group/' +
                          str(self.g1.pk) + '/',
                          {'list-new-namelist': 'user1\r\nuser2'})
        self.assertEqual(user_in_group + 2, self.g1.user_set.count())
        self.assertEqual(response.status_code, 302)

    def test_add_multipleuser_skip_badname_to_group(self):
        c = Client()
        self.login(c, 'user0')
        user_in_group = self.g1.user_set.count()
        response = c.post('/dashboard/group/' +
                          str(self.g1.pk) + '/',
                          {'list-new-namelist': 'user1\r\nnoname\r\nuser2'})
        self.assertEqual(user_in_group + 2, self.g1.user_set.count())
        self.assertEqual(response.status_code, 302)

    def test_unpermitted_add_multipleuser_to_group(self):
        c = Client()
        self.login(c, 'user3')
        user_in_group = self.g1.user_set.count()
        response = c.post('/dashboard/group/' +
                          str(self.g1.pk) + '/',
                          {'list-new-namelist': 'user1\r\nuser2'})
        self.assertEqual(user_in_group, self.g1.user_set.count())
        self.assertEqual(response.status_code, 403)

    def test_anon_add_multipleuser_to_group(self):
        c = Client()
        user_in_group = self.g1.user_set.count()
        response = c.post('/dashboard/group/' +
                          str(self.g1.pk) + '/',
                          {'list-new-namelist': 'user1\r\nuser2'})
        self.assertEqual(user_in_group, self.g1.user_set.count())
        self.assertEqual(response.status_code, 302)

    def test_anon_add_acluser_to_group(self):
        c = Client()
        gp = self.g1.profile
        acl_users = len(gp.get_users_with_level())
        response = c.post('/dashboard/group/' +
                          str(self.g1.pk) + '/acl/',
                          {'perm-new-name': 'user3', 'perm-new': 'owner'})
        self.assertEqual(acl_users, len(gp.get_users_with_level()))
        self.assertEqual(response.status_code, 302)

    def test_unpermitted_add_acluser_to_group(self):
        c = Client()
        self.login(c, 'user3')
        gp = self.g1.profile
        acl_users = len(gp.get_users_with_level())
        response = c.post('/dashboard/group/' +
                          str(self.g1.pk) + '/acl/',
                          {'perm-new-name': 'user3', 'perm-new': 'owner'})
        self.assertEqual(acl_users, len(gp.get_users_with_level()))
        self.assertEqual(response.status_code, 403)

    def test_superuser_add_acluser_to_group(self):
        c = Client()
        gp = self.g1.profile
        self.login(c, 'superuser')
        acl_users = len(gp.get_users_with_level())
        response = c.post('/dashboard/group/' +
                          str(self.g1.pk) + '/acl/',
                          {'perm-new-name': 'user3', 'perm-new': 'owner'})
        self.assertEqual(acl_users + 1, len(gp.get_users_with_level()))
        self.assertEqual(response.status_code, 302)

    def test_permitted_add_acluser_to_group(self):
        c = Client()
        gp = self.g1.profile
        self.login(c, 'user0')
        acl_users = len(gp.get_users_with_level())
        response = c.post('/dashboard/group/' +
                          str(self.g1.pk) + '/acl/',
                          {'perm-new-name': 'user3', 'perm-new': 'owner'})
        self.assertEqual(acl_users + 1, len(gp.get_users_with_level()))
        self.assertEqual(response.status_code, 302)

    def test_anon_add_aclgroup_to_group(self):
        c = Client()
        gp = self.g1.profile
        acl_groups = len(gp.get_groups_with_level())
        response = c.post('/dashboard/group/' +
                          str(self.g1.pk) + '/acl/',
                          {'perm-new-name': 'group2', 'perm-new': 'owner'})
        self.assertEqual(acl_groups, len(gp.get_groups_with_level()))
        self.assertEqual(response.status_code, 302)

    def test_unpermitted_add_aclgroup_to_group(self):
        c = Client()
        gp = self.g1.profile
        self.login(c, 'user3')
        acl_groups = len(gp.get_groups_with_level())
        response = c.post('/dashboard/group/' +
                          str(self.g1.pk) + '/acl/',
                          {'perm-new-name': 'group2', 'perm-new': 'owner'})
        self.assertEqual(acl_groups, len(gp.get_groups_with_level()))
        self.assertEqual(response.status_code, 403)

    def test_superuser_add_aclgroup_to_group(self):
        c = Client()
        gp = self.g1.profile
        self.login(c, 'superuser')
        acl_groups = len(gp.get_groups_with_level())
        response = c.post('/dashboard/group/' +
                          str(self.g1.pk) + '/acl/',
                          {'perm-new-name': 'group2', 'perm-new': 'owner'})
        self.assertEqual(acl_groups + 1, len(gp.get_groups_with_level()))
        self.assertEqual(response.status_code, 302)

    def test_permitted_add_aclgroup_to_group(self):
        c = Client()
        gp = self.g1.profile
        self.login(c, 'user0')
        acl_groups = len(gp.get_groups_with_level())
        response = c.post('/dashboard/group/' +
                          str(self.g1.pk) + '/acl/',
                          {'perm-new-name': 'group2', 'perm-new': 'owner'})
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

    def test_anon_remove_acluser_from_group(self):
        c = Client()
        gp = self.g1.profile
        acl_users = len(gp.get_users_with_level())
        response = c.post('/dashboard/group/' + str(self.g1.pk) +
                          '/remove/acl/user/' + str(self.u4.pk) + '/')
        self.assertEqual(acl_users, len(gp.get_users_with_level()))
        self.assertEqual(response.status_code, 302)

    def test_unpermitted_remove_acluser_from_group(self):
        c = Client()
        self.login(c, 'user3')
        gp = self.g1.profile
        acl_users = len(gp.get_users_with_level())
        response = c.post('/dashboard/group/' + str(self.g1.pk) +
                          '/remove/acl/user/' + str(self.u4.pk) + '/')
        self.assertEqual(acl_users, len(gp.get_users_with_level()))
        self.assertEqual(response.status_code, 403)

    def test_superuser_remove_acluser_from_group(self):
        c = Client()
        gp = self.g1.profile
        self.login(c, 'superuser')
        acl_users = len(gp.get_users_with_level())
        response = c.post('/dashboard/group/' + str(self.g1.pk) +
                          '/remove/acl/user/' + str(self.u4.pk) + '/')
        self.assertEqual(acl_users - 1, len(gp.get_users_with_level()))
        self.assertEqual(response.status_code, 302)

    def test_permitted_remove_acluser_from_group(self):
        c = Client()
        gp = self.g1.profile
        self.login(c, 'user0')
        acl_users = len(gp.get_users_with_level())
        response = c.post('/dashboard/group/' + str(self.g1.pk) +
                          '/remove/acl/user/' + str(self.u4.pk) + '/')
        self.assertEqual(acl_users - 1, len(gp.get_users_with_level()))
        self.assertEqual(response.status_code, 302)

    def test_anon_remove_aclgroup_from_group(self):
        c = Client()
        gp = self.g1.profile
        acl_groups = len(gp.get_groups_with_level())
        response = c.post('/dashboard/group/' + str(self.g1.pk) +
                          '/remove/acl/group/' + str(self.g3.pk) + '/')
        self.assertEqual(acl_groups, len(gp.get_groups_with_level()))
        self.assertEqual(response.status_code, 302)

    def test_unpermitted_remove_aclgroup_from_group(self):
        c = Client()
        self.login(c, 'user3')
        gp = self.g1.profile
        acl_groups = len(gp.get_groups_with_level())
        response = c.post('/dashboard/group/' + str(self.g1.pk) +
                          '/remove/acl/group/' + str(self.g3.pk) + '/')
        self.assertEqual(acl_groups, len(gp.get_groups_with_level()))
        self.assertEqual(response.status_code, 403)

    def test_superuser_remove_aclgroup_from_group(self):
        c = Client()
        gp = self.g1.profile
        acl_groups = len(gp.get_groups_with_level())
        self.login(c, 'superuser')
        response = c.post('/dashboard/group/' + str(self.g1.pk) +
                          '/remove/acl/group/' + str(self.g3.pk) + '/')
        self.assertEqual(acl_groups - 1, len(gp.get_groups_with_level()))
        self.assertEqual(response.status_code, 302)

    def test_permitted_remove_aclgroup_from_group(self):
        c = Client()
        gp = self.g1.profile
        acl_groups = len(gp.get_groups_with_level())
        self.login(c, 'user0')
        response = c.post('/dashboard/group/' + str(self.g1.pk) +
                          '/remove/acl/group/' + str(self.g3.pk) + '/')
        self.assertEqual(acl_groups - 1, len(gp.get_groups_with_level()))
        self.assertEqual(response.status_code, 302)


class VmDetailVncTest(LoginMixin, TestCase):
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
        response = c.get('/dashboard/vm/1/vnctoken/')
        self.assertEqual(response.status_code, 200)

    def test_not_permitted_vm_console(self):
        c = Client()
        self.login(c, 'user1')
        inst = Instance.objects.get(pk=1)
        inst.node = Node.objects.all()[0]
        inst.save()
        inst.set_level(self.u1, 'user')
        response = c.get('/dashboard/vm/1/vnctoken/')
        self.assertEqual(response.status_code, 403)


class TransferOwnershipViewTest(LoginMixin, TestCase):
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
        with self.assertRaises(SuspiciousOperation):
            c.post('/dashboard/vm/1/tx/')
        self.assertEqual(self.u2.notification_set.count(), c2)

    def test_owned_offer(self):
        c2 = self.u2.notification_set.count()
        c = Client()
        self.login(c, 'user1')
        response = c.get('/dashboard/vm/1/tx/')
        assert response.status_code == 200
        response = c.post('/dashboard/vm/1/tx/', {'name': 'user2'})
        self.assertEqual(self.u2.notification_set.count(), c2 + 1)

    def test_transfer(self):
        c = Client()
        self.login(c, 'user1')
        response = c.post('/dashboard/vm/1/tx/', {'name': 'user2'})
        url = response.context['token']
        c = Client()
        self.login(c, 'user2')
        response = c.post(url)
        self.assertEquals(Instance.objects.get(pk=1).owner.pk, self.u2.pk)

    def test_transfer_token_used_by_others(self):
        c = Client()
        self.login(c, 'user1')
        response = c.post('/dashboard/vm/1/tx/', {'name': 'user2'})
        url = response.context['token']
        response = c.post(url)  # token is for user2
        assert response.status_code == 403
        self.assertEquals(Instance.objects.get(pk=1).owner.pk, self.u1.pk)

    def test_transfer_by_superuser(self):
        c = Client()
        self.login(c, 'superuser')
        response = c.post('/dashboard/vm/1/tx/', {'name': 'user2'})
        url = response.context['token']
        c = Client()
        self.login(c, 'user2')
        response = c.post(url)
        self.assertEquals(Instance.objects.get(pk=1).owner.pk, self.u2.pk)


class RenewViewTest(LoginMixin, TestCase):
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

    def test_renew_by_owner(self):
        c = Client()
        ct = Instance.objects.get(pk=1).activity_log.\
            filter(activity_code__endswith='renew').count()
        self.login(c, 'user1')
        response = c.get('/dashboard/vm/1/renew/')
        self.assertEquals(response.status_code, 200)
        response = c.post('/dashboard/vm/1/renew/')
        self.assertEquals(response.status_code, 302)
        ct2 = Instance.objects.get(pk=1).activity_log.\
            filter(activity_code__endswith='renew').count()
        self.assertEquals(ct + 1, ct2)

    def test_renew_get_by_nonowner_wo_key(self):
        c = Client()
        self.login(c, 'user2')
        response = c.get('/dashboard/vm/1/renew/')
        self.assertEquals(response.status_code, 403)

    def test_renew_post_by_nonowner_wo_key(self):
        c = Client()
        self.login(c, 'user2')
        response = c.post('/dashboard/vm/1/renew/')
        self.assertEquals(response.status_code, 403)

    def test_renew_get_by_nonowner_w_key(self):
        key = VmRenewView.get_token_url(Instance.objects.get(pk=1), self.u2)
        c = Client()
        response = c.get(key)
        self.assertEquals(response.status_code, 200)

    def test_renew_post_by_anon_w_key(self):
        key = VmRenewView.get_token_url(Instance.objects.get(pk=1), self.u2)
        ct = Instance.objects.get(pk=1).activity_log.\
            filter(activity_code__endswith='renew').count()
        c = Client()
        response = c.post(key)
        self.assertEquals(response.status_code, 302)
        ct2 = Instance.objects.get(pk=1).activity_log.\
            filter(activity_code__endswith='renew').count()
        self.assertEquals(ct + 1, ct2)

    def test_renew_post_by_anon_w_invalid_key(self):
        class Mockinst(object):
            pk = 2
        key = VmRenewView.get_token_url(Mockinst(), self.u2)
        ct = Instance.objects.get(pk=1).activity_log.\
            filter(activity_code__endswith='renew').count()
        c = Client()
        self.login(c, 'user2')
        response = c.get(key)
        self.assertEquals(response.status_code, 404)
        response = c.post(key)
        self.assertEquals(response.status_code, 404)
        ct2 = Instance.objects.get(pk=1).activity_log.\
            filter(activity_code__endswith='renew').count()
        self.assertEquals(ct, ct2)

    def test_renew_post_by_anon_w_expired_key(self):
        key = reverse(VmRenewView.url_name, args=(
            12, 'WzEyLDFd:1WLbSi:2zIb8SUNAIRIOMTmSmKSSit2gpY'))
        ct = Instance.objects.get(pk=12).activity_log.\
            filter(activity_code__endswith='renew').count()
        c = Client()
        self.login(c, 'user2')
        response = c.get(key)
        self.assertEquals(response.status_code, 302)
        response = c.post(key)
        self.assertEquals(response.status_code, 403)
        ct2 = Instance.objects.get(pk=12).activity_log.\
            filter(activity_code__endswith='renew').count()
        self.assertEquals(ct, ct2)


class IndexViewTest(LoginMixin, TestCase):
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

        self.u1.profile.notify("urgent", "dashboard/test_message.txt", )
        response = c.get("/dashboard/")
        self.assertEqual(response.context['NEW_NOTIFICATIONS_COUNT'], 1)
