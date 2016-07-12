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
from django.contrib.auth.models import User, Permission

from mock import Mock, patch


from common.tests.celery_mock import MockCeleryMixin
from vm.models import Instance, InstanceTemplate, Lease
from dashboard.models import Profile
from request.models import Request, LeaseType, TemplateAccessType
from dashboard.tests.test_views import LoginMixin
from vm.operations import ResourcesOperation


class RequestTestBase(LoginMixin, MockCeleryMixin, TestCase):
    fixtures = ['test-vm-fixture.json', 'node.json']

    def setUp(self):
        Instance.get_remote_queue_name = Mock(return_value='test')
        self.u1 = User.objects.create(username='user1')
        self.u1.set_password('password')
        self.u1.save()
        self.us = User.objects.create(username='superuser', is_superuser=True)
        self.us.set_password('password')
        self.us.save()
        self.u1.user_permissions.add(Permission.objects.get(
            codename='create_vm'))
        # superusers are notified uppon
        for u in User.objects.filter(is_superuser=True):
            p = Profile(user=u)
            p.save()

        self.lease = Lease(name="new lease", suspend_interval_seconds=1,
                           delete_interval_seconds=1)
        self.lease.save()
        LeaseType(name="lease type #1", lease=self.lease).save()
        tat = TemplateAccessType(name="a")
        tat.save()
        tat.templates.add(InstanceTemplate.objects.get(pk=1))

    def tearDown(self):
        super(RequestTestBase, self).tearDown()
        self.u1.delete()
        self.us.delete()


class ResourceRequestTest(RequestTestBase):
    def test_resources_request(self):
        c = Client()
        self.login(c, "user1")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u1, 'owner')

        req_count = Request.objects.count()
        resp = c.post("/request/resource/1/", {
            'num_cores': 5,
            'ram_size': 512,
            'priority': 30,
            'message': "szia",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(req_count + 1, Request.objects.count())
        new_request = Request.objects.latest("pk")
        self.assertEqual(new_request.status, "PENDING")

        self.assertEqual(inst.num_cores, 2)
        self.assertEqual(inst.ram_size, 200)
        self.assertEqual(inst.priority, 10)

        # workaround for NOSTATE
        inst.emergency_change_state(new_state="STOPPED", system=True)
        with patch.object(ResourcesOperation, 'async') as mock_method:
            mock_method.side_effect = (
                new_request.action.instance.resources_change)
            new_request.accept(self.us)

        inst = Instance.objects.get(pk=1)
        self.assertEqual(inst.num_cores, 5)
        self.assertEqual(inst.ram_size, 512)
        self.assertEqual(inst.priority, 30)

        new_request = Request.objects.latest("pk")
        self.assertEqual(new_request.status, "ACCEPTED")


class TemplateAccessRequestTest(RequestTestBase):
    def test_template_access_request(self):
        c = Client()
        self.login(c, "user1")
        template = InstanceTemplate.objects.get(pk=1)
        self.assertFalse(template.has_level(self.u1, "user"))

        req_count = Request.objects.count()
        resp = c.post("/request/template/", {
            'template': 1,
            'level': "user",
            'message': "szia",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(req_count + 1, Request.objects.count())
        new_request = Request.objects.latest("pk")
        self.assertEqual(new_request.status, "PENDING")

        new_request.accept(self.us)

        new_request = Request.objects.latest("pk")
        self.assertEqual(new_request.status, "ACCEPTED")
        self.assertTrue(template.has_level(self.u1, "user"))


class LeaseRequestTest(RequestTestBase):
    def test_lease_request(self):
        c = Client()
        self.login(c, "user1")
        inst = Instance.objects.get(pk=1)
        inst.set_level(self.u1, 'owner')

        req_count = Request.objects.count()
        resp = c.post("/request/lease/1/", {
            'lease': 1,
            'message': "szia",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(req_count + 1, Request.objects.count())
        new_request = Request.objects.latest("pk")
        self.assertEqual(new_request.status, "PENDING")

        new_request.accept(self.us)

        inst = Instance.objects.get(pk=1)
        new_request = Request.objects.latest("pk")
        self.assertEqual(new_request.status, "ACCEPTED")
        self.assertEqual(inst.lease, self.lease)
