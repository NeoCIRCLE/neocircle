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

import unittest
from factory import Factory, Sequence
from mock import patch, MagicMock

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, Http404

from ..views import InstanceActivityDetail, InstanceActivity
from ..views import vm_ops, Instance


class ViewUserTestCase(unittest.TestCase):

    def test_404(self):
        view = InstanceActivityDetail.as_view()
        request = FakeRequestFactory(superuser=True)
        with self.assertRaises(Http404):
            view(request, pk=1234)

    def test_not_superuser(self):
        request = FakeRequestFactory(superuser=False)
        with patch.object(InstanceActivityDetail, 'get_object') as go:
            go.return_value = MagicMock(spec=InstanceActivity)
            go.return_value._meta.object_name = "InstanceActivity"
            view = InstanceActivityDetail.as_view()
            self.assertEquals(view(request, pk=1234).status_code, 302)

    def test_found(self):
        request = FakeRequestFactory(superuser=True)

        with patch.object(InstanceActivityDetail, 'get_object') as go:
            act = MagicMock(spec=InstanceActivity)
            act._meta.object_name = "InstanceActivity"
            go.return_value = act
            view = InstanceActivityDetail.as_view()
            self.assertEquals(view(request, pk=1234).render().status_code, 200)


class VmOperationViewTestCase(unittest.TestCase):

    def test_available(self):
        request = FakeRequestFactory(superuser=True)
        view = vm_ops['destroy']

        with patch.object(view, 'get_object') as go:
            inst = MagicMock(spec=Instance)
            inst._meta.object_name = "Instance"
            inst.destroy = Instance._ops['destroy'](inst)
            go.return_value = inst
            self.assertEquals(
                view.as_view()(request, pk=1234).render().status_code, 200)

    def test_unpermitted(self):
        request = FakeRequestFactory()
        view = vm_ops['destroy']

        with patch.object(view, 'get_object') as go:
            inst = MagicMock(spec=Instance)
            inst._meta.object_name = "Instance"
            inst.destroy = Instance._ops['destroy'](inst)
            inst.has_level.return_value = False
            go.return_value = inst
            with self.assertRaises(PermissionDenied):
                view.as_view()(request, pk=1234).render()

    def test_migrate(self):
        request = FakeRequestFactory(POST={'node': 1})
        view = vm_ops['migrate']

        with patch.object(view, 'get_object') as go, \
                patch('dashboard.views.messages') as msg, \
                patch('dashboard.views.get_object_or_404') as go4:
            inst = MagicMock(spec=Instance)
            inst._meta.object_name = "Instance"
            inst.migrate = Instance._ops['migrate'](inst)
            inst.migrate.async = MagicMock()
            inst.has_level.return_value = True
            go.return_value = inst
            go4.return_value = MagicMock()
            assert view.as_view()(request, pk=1234)['location']
            assert not msg.error.called

    def test_migrate_failed(self):
        request = FakeRequestFactory(POST={'node': 1})
        view = vm_ops['migrate']

        with patch.object(view, 'get_object') as go, \
                patch('dashboard.views.messages') as msg, \
                patch('dashboard.views.get_object_or_404') as go4:
            inst = MagicMock(spec=Instance)
            inst._meta.object_name = "Instance"
            inst.migrate = Instance._ops['migrate'](inst)
            inst.migrate.async = MagicMock()
            inst.migrate.async.side_effect = Exception
            inst.has_level.return_value = True
            go.return_value = inst
            go4.return_value = MagicMock()
            assert view.as_view()(request, pk=1234)['location']
            assert msg.error.called

    def test_migrate_template(self):
        request = FakeRequestFactory()
        view = vm_ops['migrate']

        with patch.object(view, 'get_object') as go:
            inst = MagicMock(spec=Instance)
            inst._meta.object_name = "Instance"
            inst.migrate = Instance._ops['migrate'](inst)
            inst.has_level.return_value = True
            go.return_value = inst
            self.assertEquals(
                view.as_view()(request, pk=1234).render().status_code, 200)

    def test_save_as_wo_name(self):
        request = FakeRequestFactory(POST={})
        view = vm_ops['save_as_template']

        with patch.object(view, 'get_object') as go, \
                patch('dashboard.views.messages') as msg, \
                patch('dashboard.views.get_object_or_404') as go4:
            inst = MagicMock(spec=Instance)
            inst._meta.object_name = "Instance"
            inst.save_as_template = Instance._ops['save_as_template'](inst)
            inst.save_as_template.async = MagicMock()
            inst.has_level.return_value = True
            go.return_value = inst
            go4.return_value = MagicMock()
            assert view.as_view()(request, pk=1234)['location']
            assert not msg.error.called

    def test_save_as_w_name(self):
        request = FakeRequestFactory(POST={'name': 'foobar'})
        view = vm_ops['save_as_template']

        with patch.object(view, 'get_object') as go, \
                patch('dashboard.views.messages') as msg, \
                patch('dashboard.views.get_object_or_404') as go4:
            inst = MagicMock(spec=Instance)
            inst._meta.object_name = "Instance"
            inst.save_as_template = Instance._ops['save_as_template'](inst)
            inst.save_as_template.async = MagicMock()
            inst.has_level.return_value = True
            go.return_value = inst
            go4.return_value = MagicMock()
            assert view.as_view()(request, pk=1234)['location']
            assert not msg.error.called

    def test_save_as_failed(self):
        request = FakeRequestFactory(POST={})
        view = vm_ops['save_as_template']

        with patch.object(view, 'get_object') as go, \
                patch('dashboard.views.messages') as msg, \
                patch('dashboard.views.get_object_or_404') as go4:
            inst = MagicMock(spec=Instance)
            inst._meta.object_name = "Instance"
            inst.save_as_template = Instance._ops['save_as_template'](inst)
            inst.save_as_template.async = MagicMock()
            inst.save_as_template.async.side_effect = Exception
            inst.has_level.return_value = True
            go.return_value = inst
            go4.return_value = MagicMock()
            assert view.as_view()(request, pk=1234)['location']
            assert msg.error.called

    def test_save_as_template(self):
        request = FakeRequestFactory()
        view = vm_ops['save_as_template']

        with patch.object(view, 'get_object') as go:
            inst = MagicMock(spec=Instance)
            inst._meta.object_name = "Instance"
            inst.name = 'foo'
            inst.save_as_template = Instance._ops['save_as_template'](inst)
            inst.has_level.return_value = True
            go.return_value = inst
            rend = view.as_view()(request, pk=1234).render()
            self.assertEquals(rend.status_code, 200)
            assert 'foo v1' in rend.content


def FakeRequestFactory(*args, **kwargs):
    ''' FakeRequestFactory, FakeMessages and FakeRequestContext are good for
    mocking out django views; they are MUCH faster than the Django test client.
    '''

    user = UserFactory()
    user.is_authenticated = lambda: kwargs.get('authenticated', True)
    user.is_superuser = kwargs.get('superuser', False)

    request = HttpRequest()
    request.user = user
    request.session = kwargs.get('session', {})
    if kwargs.get('POST') is not None:
        request.method = 'POST'
        request.POST = kwargs.get('POST')
    else:
        request.method = 'GET'
        request.GET = kwargs.get('GET', {})

    return request


class UserFactory(Factory):
    ''' using the excellent factory_boy library '''
    FACTORY_FOR = User
    username = Sequence(lambda i: 'test%d' % i)
    first_name = 'John'
    last_name = 'Doe'
    email = Sequence(lambda i: 'test%d@example.com' % i)
