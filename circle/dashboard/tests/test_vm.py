from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User, Group


class VmDetailTest(TestCase):
    fixtures = ['test-vm-fixture.json']

    def setUp(self):
        self.u1 = User.objects.create(username='user1')
        self.u2 = User.objects.create(username='user2', is_staff=True)
        self.us = User.objects.create(username='superuser', is_superuser=True)
        self.g1 = Group.objects.create(name='group1')
        self.g1.user_set.add(self.u1)
        self.g1.user_set.add(self.u2)
        self.g1.save()

    def test_404_vm_page(self):
        c = Client()
        response = c.get('/dashboard/vm/235555/')
        self.assertEqual(response.status_code, 404)

    def test_vm_page(self):
        c = Client()
        response = c.get('/dashboard/vm/1/')
        self.assertEqual(response.status_code, 200)
