from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User, Group

from vm.models import Instance


class VmDetailTest(TestCase):
    fixtures = ['test-vm-fixture.json']

    def setUp(self):
        self.u1 = User.objects.create(username='user1')
        self.u1.set_password('password')
        self.u1.save()
        self.u2 = User.objects.create(username='user2', is_staff=True)
        self.u2.set_password('password')
        self.u2.save()
        self.us = User.objects.create(username='superuser', is_superuser=True)
        self.us.save()
        self.g1 = Group.objects.create(name='group1')
        self.g1.user_set.add(self.u1)
        self.g1.user_set.add(self.u2)
        self.g1.save()

    def tearDown(self):
        super(VmDetailTest, self).tearDown()
        self.u1.delete()
        self.u2.delete()
        self.us.delete()
        self.g1.delete()

    def login(self, client, username, password='password'):
        response = client.post('/accounts/login/', {'username': username,
                                                    'password': password})
        self.assertNotEqual(response.status_code, 403)

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
