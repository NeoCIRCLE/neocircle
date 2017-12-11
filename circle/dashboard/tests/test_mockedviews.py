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
import warnings

from factory import Factory, Sequence
from mock import patch, MagicMock

from django.contrib.auth.models import User, AnonymousUser
from django.core.exceptions import PermissionDenied
from django.core.signing import TimestampSigner, JSONSerializer, b64_encode
from django.http import HttpRequest, Http404, QueryDict
from django.utils import baseconv

from ..models import Profile
from ..views import InstanceActivityDetail, InstanceActivity
from ..views import vm_ops, vm_mass_ops, Instance, UnsubscribeFormView
from ..views import AclUpdateView
from .. import views


class QuerySet(list):
    model = MagicMock()

    def get(self, *args, **kwargs):
        return self.pop()


class ViewUserTestCase(unittest.TestCase):

    def test_404(self):
        view = InstanceActivityDetail.as_view()
        request = FakeRequestFactory(superuser=True)
        with self.assertRaises(Http404):
            view(request, pk=1234)

    def test_not_superuser(self):
        request = FakeRequestFactory(superuser=False)
        with patch.object(InstanceActivityDetail, 'get_object') as go:
            go.return_value = MagicMock(spec=InstanceActivity,
                                        activity_code='test.test')
            go.return_value._meta.object_name = "InstanceActivity"
            view = InstanceActivityDetail.as_view()
            self.assertEquals(view(request, pk=1234).status_code, 200)

    def test_found(self):
        request = FakeRequestFactory(superuser=True)

        with patch.object(InstanceActivityDetail, 'get_object') as go:
            act = MagicMock(spec=InstanceActivity,
                            activity_code='test.test')
            act._meta.object_name = "InstanceActivity"
            act.user.pk = 1
            go.return_value = act
            view = InstanceActivityDetail.as_view()
            self.assertEquals(view(request, pk=1234).render().status_code, 200)


class ExpiredSigner(TimestampSigner):
    def timestamp(self):
        return baseconv.base62.encode(1)

    @classmethod
    def dumps(cls, obj, key=None, salt='django.core.signing',
              serializer=JSONSerializer, compress=False):
            data = serializer().dumps(obj)
            base64d = b64_encode(data)
            return cls(key, salt=salt).sign(base64d)


class SubscribeTestCase(unittest.TestCase):

    @patch.object(views.UnsubscribeFormView, 'get_queryset')
    @patch.object(views.UnsubscribeFormView, 'form_valid')
    def test_change(self, iv, gq):
            view = views.UnsubscribeFormView.as_view()
            p = MagicMock(spec=Profile, email_notifications=True)
            gq.return_value.get.return_value = p
            token = UnsubscribeFormView.get_token(MagicMock(pk=1))
            request = FakeRequestFactory(POST={})
            self.assertEquals(view(request, token=token), iv.return_value)
            gq.return_value.get.assert_called_with(user_id=1)

    @patch.object(views.UnsubscribeFormView, 'get_queryset')
    @patch.object(views.UnsubscribeFormView, 'form_valid')
    def test_change_to_true(self, iv, gq):
            view = views.UnsubscribeFormView.as_view()
            p = MagicMock(spec=Profile, email_notifications=False)
            gq.return_value.get.return_value = p
            token = UnsubscribeFormView.get_token(MagicMock(pk=1))
            request = FakeRequestFactory(POST={'email_notifications': 'on'})
            self.assertEquals(view(request, token=token), iv.return_value)
            gq.return_value.get.assert_called_with(user_id=1)

    def test_404_for_invalid_token(self):
        view = UnsubscribeFormView.as_view()
        request = FakeRequestFactory()
        with self.assertRaises(Http404):
            view(request, token="foo:bar")

    def test_redirect_for_old_token(self):
        oldtoken = ExpiredSigner.dumps(1, salt=UnsubscribeFormView.get_salt())
        view = UnsubscribeFormView.as_view()
        request = FakeRequestFactory()
        assert view(request, token=oldtoken)['location']

    def test_post_redirect_for_old_token(self):
        oldtoken = ExpiredSigner.dumps(1, salt=UnsubscribeFormView.get_salt())
        view = UnsubscribeFormView.as_view()
        request = FakeRequestFactory(POST={})
        assert view(request, token=oldtoken)['location']


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
        request = FakeRequestFactory(
            POST={'to_node': 1, 'live_migration': True}, superuser=True)
        view = vm_ops['migrate']
        node = MagicMock(pk=1, name='node1')

        with patch.object(view, 'get_object') as go, \
                patch('dashboard.views.util.messages') as msg, \
                patch.object(view, 'get_form_kwargs') as form_kwargs:
            inst = MagicMock(spec=Instance)
            inst._meta.object_name = "Instance"
            inst.migrate = Instance._ops['migrate'](inst)
            inst.migrate.async = MagicMock()
            inst.has_level.return_value = True
            form_kwargs.return_value = {
                'default': 100, 'choices': QuerySet([node])}
            go.return_value = inst
            assert view.as_view()(request, pk=1234)['location']
            assert not msg.error.called
            inst.migrate.async.assert_called_once_with(
                to_node=node, live_migration=True, user=request.user)

    def test_migrate_failed(self):
        request = FakeRequestFactory(POST={'to_node': 1}, superuser=True)
        view = vm_ops['migrate']
        node = MagicMock(pk=1, name='node1')

        with patch.object(view, 'get_object') as go, \
                patch('dashboard.views.util.messages') as msg, \
                patch.object(view, 'get_form_kwargs') as form_kwargs:
            inst = MagicMock(spec=Instance)
            inst._meta.object_name = "Instance"
            inst.migrate = Instance._ops['migrate'](inst)
            inst.migrate.async = MagicMock()
            inst.migrate.async.side_effect = Exception
            inst.has_level.return_value = True
            form_kwargs.return_value = {
                'default': 100, 'choices': QuerySet([node])}
            go.return_value = inst
            assert view.as_view()(request, pk=1234)['location']
            assert inst.migrate.async.called
            assert msg.error.called

    def test_migrate_wo_permission(self):
        request = FakeRequestFactory(POST={'to_node': 1}, superuser=False)
        view = vm_ops['migrate']
        node = MagicMock(pk=1, name='node1')

        with patch.object(view, 'get_object') as go, \
                patch.object(view, 'get_form_kwargs') as form_kwargs:
            inst = MagicMock(spec=Instance)
            inst._meta.object_name = "Instance"
            inst.migrate = Instance._ops['migrate'](inst)
            inst.migrate.async = MagicMock()
            inst.has_level.return_value = True
            form_kwargs.return_value = {
                'default': 100, 'choices': QuerySet([node])}
            go.return_value = inst
            with self.assertRaises(PermissionDenied):
                assert view.as_view()(request, pk=1234)['location']
            assert not inst.migrate.async.called

    def test_migrate_template(self):
        """check if GET dialog's template can be rendered"""
        request = FakeRequestFactory(superuser=True)
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
        request = FakeRequestFactory(POST={}, has_perms_mock=True)
        view = vm_ops['save_as_template']

        with patch.object(view, 'get_object') as go, \
                patch('dashboard.views.util.messages') as msg:
            inst = MagicMock(spec=Instance)
            inst.name = "asd"
            inst._meta.object_name = "Instance"
            inst.save_as_template = Instance._ops['save_as_template'](inst)
            inst.save_as_template.async = MagicMock()
            inst.has_level.return_value = True
            go.return_value = inst
            assert view.as_view()(request, pk=1234)
            assert not msg.error.called

    def test_save_as_w_name(self):
        request = FakeRequestFactory(POST={'name': 'foobar'},
                                     has_perms_mock=True)
        view = vm_ops['save_as_template']

        with patch.object(view, 'get_object') as go, \
                patch('dashboard.views.util.messages') as msg:
            inst = MagicMock(spec=Instance)
            inst.name = "asd"
            inst._meta.object_name = "Instance"
            inst.save_as_template = Instance._ops['save_as_template'](inst)
            inst.save_as_template.async = MagicMock()
            inst.has_level.return_value = True
            go.return_value = inst
            assert view.as_view()(request, pk=1234)['location']
            assert not msg.error.called

    def test_save_as_template(self):
        request = FakeRequestFactory(has_perms_mock=True)
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


class VmMassOperationViewTestCase(unittest.TestCase):

    def test_available(self):
        request = FakeRequestFactory(superuser=True)
        view = vm_mass_ops['destroy']

        with patch.object(view, 'get_object') as go:
            inst = MagicMock(spec=Instance)
            inst._meta.object_name = "Instance"
            inst.destroy = Instance._ops['destroy'](inst)
            go.return_value = [inst]
            self.assertEquals(
                view.as_view()(request, pk=1234).render().status_code, 200)

    def test_unpermitted_choice(self):
        "User has user level, but not the needed ownership."
        request = FakeRequestFactory()
        view = vm_mass_ops['destroy']

        with patch.object(view, 'get_object') as go:
            inst = MagicMock(spec=Instance)
            inst._meta.object_name = "Instance"
            inst.has_level = lambda self, l: {"user": True, "owner": False}[l]
            inst.destroy = Instance._ops['destroy'](inst)
            inst.destroy._operate = MagicMock()
            go.return_value = [inst]
            view.as_view()(request, pk=1234).render()
            assert not inst.destroy._operate.called

    def test_unpermitted(self):
        request = FakeRequestFactory()
        view = vm_mass_ops['destroy']

        with patch.object(view, 'get_object') as go:
            inst = MagicMock(spec=Instance)
            inst._meta.object_name = "Instance"
            inst.destroy = Instance._ops['destroy'](inst)
            inst.has_level.return_value = False
            go.return_value = [inst]
            with self.assertRaises(PermissionDenied):
                view.as_view()(request, pk=1234).render()

    def test_migrate(self):
        request = FakeRequestFactory(POST={'to_node': 1}, superuser=True)
        view = vm_mass_ops['migrate']

        with patch.object(view, 'get_object') as go, \
                patch('dashboard.views.util.messages') as msg, \
                patch('dashboard.views.vm.messages') as msg2:
            inst = MagicMock(spec=Instance)
            inst._meta.object_name = "Instance"
            inst.migrate = Instance._ops['migrate'](inst)
            inst.migrate.async = MagicMock()
            inst.has_level.return_value = True
            go.return_value = [inst]
            assert view.as_view()(request, pk=1234)['location']
            assert not msg.error.called
            assert not msg2.error.called

    def test_migrate_failed(self):
        request = FakeRequestFactory(POST={'to_node': 1}, superuser=True)
        view = vm_mass_ops['migrate']

        with patch.object(view, 'get_object') as go, \
                patch('dashboard.views.vm.messages') as msg:
            inst = MagicMock(spec=Instance)
            inst._meta.object_name = "Instance"
            inst.migrate = Instance._ops['migrate'](inst)
            inst.migrate.async = MagicMock()
            inst.migrate.async.side_effect = Exception
            inst.has_level.return_value = True
            go.return_value = [inst]
            assert view.as_view()(request, pk=1234)['location']
            assert msg.error.called

    def test_migrate_wo_permission(self):
        request = FakeRequestFactory(POST={'to_node': 1}, superuser=False)
        view = vm_mass_ops['migrate']

        with patch.object(view, 'get_object') as go:
            inst = MagicMock(spec=Instance)
            inst._meta.object_name = "Instance"
            inst.migrate = Instance._ops['migrate'](inst)
            inst.migrate.async = MagicMock()
            inst.has_level.return_value = True
            go.return_value = [inst]
            with self.assertRaises(PermissionDenied):
                assert view.as_view()(request, pk=1234)['location']

    def test_migrate_template(self):
        """check if GET dialog's template can be rendered"""
        request = FakeRequestFactory(superuser=True)
        view = vm_mass_ops['migrate']

        with patch.object(view, 'get_object') as go:
            inst = MagicMock(spec=Instance)
            inst._meta.object_name = "Instance"
            inst.migrate = Instance._ops['migrate'](inst)
            inst.has_level.return_value = True
            go.return_value = [inst]
            self.assertEquals(
                view.as_view()(request, pk=1234).render().status_code, 200)


class RenewViewTest(unittest.TestCase):

    def test_renew_template(self):
        request = FakeRequestFactory(has_perms_mock=True)
        view = vm_ops['renew']

        with patch.object(view, 'get_object') as go:
            inst = MagicMock(spec=Instance)
            inst._meta.object_name = "Instance"
            inst.name = 'foo'
            inst.lease = MagicMock(pk=99)
            inst.renew = Instance._ops['renew'](inst)
            inst.has_level.return_value = True
            go.return_value = inst
            rend = view.as_view()(request, pk=1234).render()
            self.assertEquals(rend.status_code, 200)

    def test_renew_by_owner_wo_param(self):
        request = FakeRequestFactory(POST={}, has_perms_mock=True)
        view = vm_ops['renew']

        with patch.object(view, 'get_object') as go, \
                patch('dashboard.views.util.messages') as msg:
            inst = MagicMock(spec=Instance)
            inst._meta.object_name = "Instance"
            inst.lease = MagicMock(pk=99)
            inst.renew = Instance._ops['renew'](inst)
            inst.renew.async = MagicMock()
            inst.has_level.return_value = True
            go.return_value = inst
            assert view.as_view()(request, pk=1234)
            assert not msg.error.called
            assert inst.renew.async.called_with(user=request.user, lease=None)
            assert inst.renew.async.return_value.get.called
            # success would redirect

    def test_renew_by_owner_w_param(self):
        request = FakeRequestFactory(POST={'length': 1}, has_perms_mock=True)
        view = vm_ops['renew']

        with patch.object(view, 'get_object') as go, \
                patch('dashboard.views.util.messages') as msg:
            inst = MagicMock(spec=Instance)
            inst._meta.object_name = "Instance"
            inst.lease = MagicMock(pk=99)
            inst.renew = Instance._ops['renew'](inst)
            inst.renew.async = MagicMock()
            inst.has_level.return_value = True
            go.return_value = inst
            assert view.as_view()(request, pk=1234)
            assert not msg.error.called

    def test_renew_get_by_anon_wo_key(self):
        request = FakeRequestFactory(authenticated=False)
        view = vm_ops['renew']

        with patch.object(view, 'get_object') as go:
            inst = MagicMock(spec=Instance)
            inst._meta.object_name = "Instance"
            inst.renew = Instance._ops['renew'](inst)
            inst.renew.async = MagicMock()
            inst.has_level.return_value = False
            go.return_value = inst
            self.assertIn('login',
                          view.as_view()(request, pk=1234)['location'])

    def test_renew_get_by_nonowner_wo_key(self):
        request = FakeRequestFactory(has_perms_mock=True)
        view = vm_ops['renew']

        with patch.object(view, 'get_object') as go:
            inst = MagicMock(spec=Instance)
            inst._meta.object_name = "Instance"
            inst.renew = Instance._ops['renew'](inst)
            inst.renew.async = MagicMock()
            inst.has_level.return_value = False
            go.return_value = inst
            with self.assertRaises(PermissionDenied):
                assert view.as_view()(request, pk=1234)

    def test_renew_post_by_nonowner_wo_key(self):
        request = FakeRequestFactory(POST={'length': 1}, has_perms_mock=True)
        view = vm_ops['renew']

        with patch.object(view, 'get_object') as go:
            inst = MagicMock(spec=Instance, pk=11)
            inst._meta.object_name = "Instance"
            inst.lease = MagicMock(pk=99)
            inst.renew = Instance._ops['renew'](inst)
            inst.renew.async = MagicMock()
            inst.has_level.return_value = False
            go.return_value = inst
            with self.assertRaises(PermissionDenied):
                assert view.as_view()(request, pk=1234)

    def test_renew_get_by_nonowner_w_key(self):
        user = FakeRequestFactory(superuser=True).user
        view = vm_ops['renew']
        inst = MagicMock(spec=Instance, pk=11)
        inst._meta.object_name = "Instance"
        inst.renew = Instance._ops['renew'](inst)
        inst.renew.async = MagicMock()
        key = view.get_token_url(inst, user).split('?')[1].split('=')[1]
        request = FakeRequestFactory(GET={'k': key})  # other user!

        with patch.object(view, 'get_object') as go, \
                patch('dashboard.views.User.objects') as gu, \
                patch('dashboard.views.Lease.get_objects_with_level') as gol:
            gol.return_value = views.Lease.objects.all()
            gu.get.return_value = user
            go.return_value = inst
            assert view.as_view()(request, pk=1234).render().status_code == 200

    def test_renew_post_by_anon_w_key(self):
        user = FakeRequestFactory(authenticated=True).user
        view = vm_ops['renew']
        inst = MagicMock(spec=Instance, pk=11)
        inst._meta.object_name = "Instance"
        inst.renew = Instance._ops['renew'](inst)
        inst.renew.async = MagicMock()
        inst.has_level = lambda user, level: user.is_authenticated()
        key = view.get_token_url(inst, user).split('?')[1].split('=')[1]
        request = FakeRequestFactory(GET={'k': key}, authenticated=False)

        with patch.object(view, 'get_object') as go, \
                patch('dashboard.views.Lease.get_objects_with_level') as gol:
            go.return_value = inst
            gol.return_value = views.Lease.objects.all()
            assert view.as_view()(request, pk=1234).render().status_code == 200

    def test_renew_post_by_anon_w_invalid_key(self):
        view = vm_ops['renew']
        key = "invalid"
        inst = MagicMock(spec=Instance, pk=11)
        inst._meta.object_name = "Instance"
        inst.renew = Instance._ops['renew'](inst)
        inst.renew.async = MagicMock()
        inst.has_level.return_value = False
        request = FakeRequestFactory(GET={'k': key}, authenticated=False)
        with patch.object(view, 'get_object') as go:
            go.return_value = inst
            self.assertIn('login',
                          view.as_view()(request, pk=1234)['location'])

    def test_renew_post_by_anon_w_expired_key(self):

        def side(max_age=None, *args, **kwargs):
            if max_age:
                raise views.signing.BadSignature

        user = FakeRequestFactory(authenticated=False).user
        view = vm_ops['renew']
        inst = MagicMock(spec=Instance, pk=11)
        inst._meta.object_name = "Instance"
        inst.renew = Instance._ops['renew'](inst)
        inst.renew.async = MagicMock()
        inst.has_level.return_value = False
        key = view.get_token_url(inst, user).split('?')[1].split('=')[1]
        with patch('dashboard.views.signing.loads') as loader, \
                patch.object(view, 'get_object') as go:
            loader.return_value = (inst.pk, user.pk)

            loader.side_effect = side
            request = FakeRequestFactory(GET={'k': key}, user=user)
            go.return_value = inst
            self.assertIn('login',
                          view.as_view()(request, pk=1234)['location'])


class AclUpdateViewTest(unittest.TestCase):
    def test_has_next_level(self):
        data = {None: 'user', 'user': 'operator', 'operator': 'owner',
                'owner': 'owner'}
        for k, v in data.items():
            inst = MagicMock(spec=Instance)
            inst.has_level.return_value = True
            inst.ACL_LEVELS = Instance.ACL_LEVELS

            self.assertTrue(AclUpdateView.has_next_level('dummy', inst, k))
            inst.has_level.assert_called_with('dummy', v)

    def test_set_level_mod_owner(self):
        with patch('dashboard.views.util.messages') as msg:
            request = FakeRequestFactory(POST={})

            inst = MagicMock(spec=Instance)
            inst.owner = request.user

            v = AclUpdateView()
            v.instance = inst
            v.request = request
            v.get_level = MagicMock(return_value='owner')
            v.check_auth = MagicMock(side_effect=Exception(''))

            v.set_level(request.user, 'user')
            v.get_level.assert_called_with(request.user)
            assert not v.check_auth.called
            assert msg.warning.called

    def test_set_level_permitted(self):
        data = (('user', 'owner', ('user', 'operator', 'owner'), False),
                (None, None, ('user', ), True),
                ('user', None, ('user', ), True),
                (None, 'user', ('user', ), True),
                ('operator', 'owner', ('user', 'operator'), True),
                (None, 'user', ('user', 'operator'), False))

        for old_level, new_level, allowed_levels, fail in data:
            with patch('dashboard.views.util.messages') as msg:
                def has_level(user, level):
                    return level in allowed_levels

                request = FakeRequestFactory(POST={})

                inst = MagicMock(spec=Instance)
                inst.has_level.side_effect = has_level
                inst.ACL_LEVELS = Instance.ACL_LEVELS

                v = AclUpdateView()
                v.instance = inst
                v.request = request
                v.is_owner = True
                v.get_level = MagicMock(return_value=old_level)

                v.set_level(request.user, new_level)

                v.get_level.assert_called_with(request.user)
                assert (new_level == old_level) ^ inst.has_level.called
                assert fail ^ inst.set_level.called
                assert fail ^ msg.success.called

    def test_readd(self):
        request = FakeRequestFactory(POST={'name': 'user0', 'level': 'user'})
        with patch('dashboard.views.util.messages') as msg:
            with patch.object(AclUpdateView, 'get_object') as go:
                view = AclUpdateView.as_view()
                inst = MagicMock(spec=Instance)
                go.return_value = inst
                view(request)
                assert msg.warning.called


def FakeRequestFactory(user=None, **kwargs):
    ''' FakeRequestFactory, FakeMessages and FakeRequestContext are good for
    mocking out django views; they are MUCH faster than the Django test client.
    '''

    if user is None:
        auth = kwargs.pop('authenticated', True)
        user = UserFactory() if auth else AnonymousUser()
        user.is_superuser = kwargs.pop('superuser', False)
        if kwargs.pop('has_perms_mock', False):
            user.has_perms = MagicMock(return_value=True)
        if auth:
            user.save()

    request = HttpRequest()
    request.user = user
    request.session = kwargs.pop('session', {})
    if kwargs.get('POST') is not None:
        request.method = 'POST'
        request.POST = QueryDict('', mutable=True)
        request.POST.update(kwargs.pop('POST'))
    else:
        request.method = 'GET'
    request.GET = QueryDict('', mutable=True)
    request.GET.update(kwargs.pop('GET', {}))

    if len(kwargs):
        warnings.warn("FakeRequestFactory kwargs unused: " + unicode(kwargs),
                      stacklevel=2)

    return request


class UserFactory(Factory):
    ''' using the excellent factory_boy library '''
    FACTORY_FOR = User
    username = Sequence(lambda i: 'test%d' % i)
    first_name = 'John'
    last_name = 'Doe'
    email = Sequence(lambda i: 'test%d@example.com' % i)
