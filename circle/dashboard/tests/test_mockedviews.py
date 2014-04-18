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
    if kwargs.get('POST'):
        request.method = 'POST'
        request.POST = kwargs.get('POST')
    else:
        request.method = 'GET'
        request.POST = kwargs.get('GET', {})

    return request


class UserFactory(Factory):
    ''' using the excellent factory_boy library '''
    FACTORY_FOR = User
    username = Sequence(lambda i: 'test%d' % i)
    first_name = 'John'
    last_name = 'Doe'
    email = Sequence(lambda i: 'test%d@example.com' % i)
