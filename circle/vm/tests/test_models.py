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

from datetime import datetime
from mock import Mock, MagicMock, patch, call
import types

from celery.contrib.abortable import AbortableAsyncResult
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils.translation import ugettext_lazy as _

from ..models import (
    Lease, Node, Interface, Instance, InstanceTemplate, InstanceActivity,
)
from ..models.instance import find_unused_port, ActivityInProgressError
from ..operations import (
    DeployOperation, DestroyOperation, FlushOperation, MigrateOperation,
)


class PortFinderTestCase(TestCase):

    def test_find_unused_port_without_used_ports(self):
        port = find_unused_port(port_range=(1000, 2000))
        assert port is not None

    def test_find_unused_port_with_fully_saturated_range(self):
        r = (10, 20)
        port = find_unused_port(port_range=r, used_ports=range(*r))
        assert port is None


class TemplateTestCase(TestCase):

    def test_template_creation(self):
        template = InstanceTemplate(name='My first template',
                                    access_method='ssh', )
        template.clean()
        # TODO add images & net


class InstanceTestCase(TestCase):

    def test_is_running(self):
        inst = MagicMock(status='RUNNING')
        self.assertTrue(Instance.is_running.fget(inst))

    def test_mon_stopped_while_activity_running(self):
        node = Mock()
        port = Mock()
        inst = MagicMock(spec=Instance, node=node, vnc_port=port)
        inst.save.side_effect = AssertionError
        with patch('vm.models.instance.InstanceActivity') as ia:
            ia.create.side_effect = ActivityInProgressError(MagicMock())
            Instance.vm_state_changed(inst, 'STOPPED')
        self.assertEquals(inst.node, node)
        self.assertEquals(inst.vnc_port, port)

    def test_deploy_destroyed(self):
        inst = Mock(destroyed_at=datetime.now(), spec=Instance,
                    InstanceDestroyedError=Instance.InstanceDestroyedError)
        deploy_op = DeployOperation(inst)
        with patch.object(DeployOperation, 'create_activity'):
            with self.assertRaises(Instance.InstanceDestroyedError):
                deploy_op(system=True)

    def test_destroy_destroyed(self):
        inst = Mock(destroyed_at=datetime.now(), spec=Instance,
                    InstanceDestroyedError=Instance.InstanceDestroyedError)
        destroy_op = DestroyOperation(inst)
        with patch.object(DestroyOperation, 'create_activity'):
            with self.assertRaises(Instance.InstanceDestroyedError):
                destroy_op(system=True)
        self.assertFalse(inst.save.called)

    def test_destroy_sets_destroyed(self):
        inst = Mock(destroyed_at=None, spec=Instance,
                    InstanceDestroyedError=Instance.InstanceDestroyedError)
        inst.node = MagicMock(spec=Node)
        inst.disks.all.return_value = []
        destroy_op = DestroyOperation(inst)
        with patch.object(DestroyOperation, 'create_activity'):
            destroy_op(system=True)
        self.assertTrue(inst.destroyed_at)
        inst.save.assert_called()

    def test_migrate_with_scheduling(self):
        inst = Mock(destroyed_at=None, spec=Instance)
        inst.interface_set.all.return_value = []
        inst.node = MagicMock(spec=Node)
        inst.status = 'RUNNING'
        migrate_op = MigrateOperation(inst)
        with patch('vm.models.instance.vm_tasks.migrate') as migr:
            act = MagicMock()
            with patch.object(MigrateOperation, 'create_activity',
                              return_value=act):
                migrate_op(system=True)

            migr.apply_async.assert_called()
            self.assertIn(call.sub_activity(u'scheduling'), act.mock_calls)
            inst.select_node.assert_called()

    def test_migrate_wo_scheduling(self):
        inst = MagicMock(destroyed_at=None, spec=Instance)
        inst.interface_set.all.return_value = []
        inst.node = MagicMock(spec=Node)
        inst.status = 'RUNNING'
        migrate_op = MigrateOperation(inst)
        with patch('vm.models.instance.vm_tasks.migrate') as migr:
            inst.select_node.side_effect = AssertionError
            act = MagicMock()
            with patch.object(MigrateOperation, 'create_activity',
                              return_value=act):
                migrate_op(to_node=inst.node, system=True)

            migr.apply_async.assert_called()
            self.assertNotIn(call.sub_activity(u'scheduling'), act.mock_calls)

    def test_migrate_with_error(self):
        inst = Mock(destroyed_at=None, spec=Instance)
        inst.interface_set.all.return_value = []
        inst.node = MagicMock(spec=Node)
        inst.status = 'RUNNING'
        e = Exception('abc')
        setattr(e, 'libvirtError', '')
        inst.migrate_vm.side_effect = e
        migrate_op = MigrateOperation(inst)
        with patch('vm.models.instance.vm_tasks.migrate') as migr:
            act = MagicMock()
            with patch.object(MigrateOperation, 'create_activity',
                              return_value=act):
                self.assertRaises(Exception, migrate_op, system=True)

            migr.apply_async.assert_called()
            self.assertIn(call.sub_activity(u'scheduling'), act.mock_calls)
            self.assertIn(call.sub_activity(u'rollback_net'), act.mock_calls)
            inst.select_node.assert_called()

    def test_status_icon(self):
        inst = MagicMock(spec=Instance)
        inst.status = 'dummy-value'
        self.assertEqual(Instance.get_status_icon(inst), 'icon-question-sign')
        inst.status = 'RUNNING'
        self.assertEqual(Instance.get_status_icon(inst), 'icon-play')


class InterfaceTestCase(TestCase):

    def test_interface_create(self):
        from firewall.models import Vlan, Domain
        owner = User()
        owner.save()
        i = Instance(id=10, owner=owner, access_method='rdp')
        d = Domain(owner=owner)
        d.save()
        v = Vlan(vid=55, network4='127.0.0.1/8',
                 network6='2001::1/32', domain=d)
        v.save()
        Interface.create(i, v, managed=True, owner=owner)


class LeaseTestCase(TestCase):

    fixtures = ['lease.json']

    def test_methods(self):
        from datetime import timedelta
        td = timedelta(seconds=1)
        l = Lease.objects.get(pk=1)

        assert "never" not in unicode(l)
        assert l.delete_interval > td
        assert l.suspend_interval > td

        l.delete_interval = None
        assert "never" in unicode(l)
        assert l.delete_interval is None

        l.delete_interval = td * 2
        assert "never" not in unicode(l)

        l.suspend_interval = None
        assert "never" in unicode(l)


class NodeTestCase(TestCase):

    def test_state(self):
        node = Mock(spec=Node)
        node.online = True
        node.enabled = True
        node.STATES = Node.STATES
        self.assertEqual(Node.get_state(node), "ONLINE")
        assert isinstance(Node.get_status_display(node), _("").__class__)


class InstanceActivityTestCase(TestCase):

    def test_create_concurrency_check(self):
        instance = MagicMock(spec=Instance)
        instance.activity_log.filter.return_value.exists.return_value = True

        with self.assertRaises(ActivityInProgressError):
            InstanceActivity.create('test', instance, concurrency_check=True)

    def test_create_no_concurrency_check(self):
        instance = MagicMock(spec=Instance)
        instance.activity_log.filter.return_value.exists.return_value = True
        mock_instance_activity_cls = MagicMock(spec=InstanceActivity,
                                               ACTIVITY_CODE_BASE='test')

        original_create = InstanceActivity.create
        mocked_create = types.MethodType(original_create.im_func,
                                         mock_instance_activity_cls,
                                         original_create.im_class)
        try:
            mocked_create('test', instance, concurrency_check=False)
        except ActivityInProgressError:
            raise AssertionError("'create' method checked for concurrent "
                                 "activities.")

    def test_create_sub_concurrency_check(self):
        iaobj = MagicMock(spec=InstanceActivity)
        iaobj.children.filter.return_value.exists.return_value = True

        with self.assertRaises(ActivityInProgressError):
            InstanceActivity.create_sub(iaobj, "test", concurrency_check=True)

    def test_create_sub_no_concurrency_check(self):
        iaobj = MagicMock(spec=InstanceActivity)
        iaobj.activity_code = 'test'
        iaobj.children.filter.return_value.exists.return_value = True

        create_sub_func = InstanceActivity.create_sub
        with patch('vm.models.activity.InstanceActivity'):
            try:
                create_sub_func(iaobj, 'test', concurrency_check=False)
            except ActivityInProgressError:
                raise AssertionError("'create_sub' method checked for "
                                     "concurrent activities.")

    def test_is_abortable(self):
        get_op = MagicMock(return_value=MagicMock(abortable=True))
        instance = MagicMock(get_operation_from_activity_code=get_op)
        iaobj = MagicMock(spec=InstanceActivity, activity_code='test',
                          finished=False, instance=instance, task_uuid='test')
        self.assertTrue(InstanceActivity.is_abortable.fget(iaobj))

    def test_not_abortable_when_not_associated_with_task(self):
        get_op = MagicMock(return_value=MagicMock(abortable=True))
        instance = MagicMock(get_operation_from_activity_code=get_op)
        iaobj = MagicMock(spec=InstanceActivity, activity_code='test',
                          finished=False, instance=instance, task_uuid=None)
        self.assertFalse(InstanceActivity.is_abortable.fget(iaobj))

    def test_not_abortable_when_finished(self):
        get_op = MagicMock(return_value=MagicMock(abortable=True))
        instance = MagicMock(get_operation_from_activity_code=get_op)
        iaobj = MagicMock(spec=InstanceActivity, activity_code='test',
                          finished=True, instance=instance, task_uuid='test')
        self.assertFalse(InstanceActivity.is_abortable.fget(iaobj))

    def test_not_abortable_when_operation_not_abortable(self):
        get_op = MagicMock(return_value=MagicMock(abortable=False))
        instance = MagicMock(get_operation_from_activity_code=get_op)
        iaobj = MagicMock(spec=InstanceActivity, activity_code='test',
                          finished=False, instance=instance, task_uuid='test')
        self.assertFalse(InstanceActivity.is_abortable.fget(iaobj))

    def test_not_abortable_when_no_matching_operation(self):
        get_op = MagicMock(return_value=None)
        instance = MagicMock(get_operation_from_activity_code=get_op)
        iaobj = MagicMock(spec=InstanceActivity, activity_code='test',
                          finished=False, instance=instance, task_uuid='test')
        self.assertFalse(InstanceActivity.is_abortable.fget(iaobj))

    def test_not_aborted_when_not_associated_with_task(self):
        iaobj = MagicMock(task_uuid=None)
        self.assertFalse(InstanceActivity.is_aborted.fget(iaobj))

    def test_is_aborted_when_associated_task_is_aborted(self):
        expected = object()
        iaobj = MagicMock(task_uuid='test')
        with patch.object(AbortableAsyncResult, 'is_aborted',
                          return_value=expected):
            self.assertEquals(expected,
                              InstanceActivity.is_aborted.fget(iaobj))

    def test_is_abortable_for_activity_owner_if_not_abortable(self):
        iaobj = MagicMock(spec=InstanceActivity, is_abortable=False,
                          user=MagicMock(spec=User, is_superuser=False))
        self.assertFalse(InstanceActivity.is_abortable_for(iaobj, iaobj.user))

    def test_is_abortable_for_instance_owner(self):
        get_op = MagicMock(return_value=MagicMock(abortable=True))
        instance = MagicMock(get_operation_from_activity_code=get_op,
                             owner=MagicMock(spec=User, is_superuser=False))
        iaobj = MagicMock(spec=InstanceActivity, activity_code='test',
                          finished=False, instance=instance, task_uuid='test',
                          user=MagicMock(spec=User, is_superuser=False))
        self.assertTrue(
            InstanceActivity.is_abortable_for(iaobj, iaobj.instance.owner))

    def test_is_abortable_for_activity_owner(self):
        get_op = MagicMock(return_value=MagicMock(abortable=True))
        instance = MagicMock(get_operation_from_activity_code=get_op)
        iaobj = MagicMock(spec=InstanceActivity, activity_code='test',
                          finished=False, instance=instance, task_uuid='test',
                          user=MagicMock(spec=User, is_superuser=False))
        self.assertTrue(InstanceActivity.is_abortable_for(iaobj, iaobj.user))

    def test_not_abortable_for_foreign(self):
        get_op = MagicMock(return_value=MagicMock(abortable=True))
        instance = MagicMock(get_operation_from_activity_code=get_op)
        iaobj = MagicMock(spec=InstanceActivity, activity_code='test',
                          finished=False, instance=instance, task_uuid='test')
        self.assertFalse(InstanceActivity.is_abortable_for(
            iaobj, MagicMock(spec=User, is_superuser=False)))

    def test_is_abortable_for_superuser(self):
        get_op = MagicMock(return_value=MagicMock(abortable=True))
        instance = MagicMock(get_operation_from_activity_code=get_op)
        iaobj = MagicMock(spec=InstanceActivity, activity_code='test',
                          finished=False, instance=instance, task_uuid='test')
        su = MagicMock(spec=User, is_superuser=True)
        self.assertTrue(InstanceActivity.is_abortable_for(iaobj, su))

    def test_disable_enabled(self):
        node = MagicMock(spec=Node, enabled=True)
        with patch('vm.models.node.node_activity') as nac:
            na = MagicMock()
            nac.return_value = na
            na.__enter__.return_value = MagicMock()
            Node.disable(node)
        self.assertFalse(node.enabled)
        node.save.assert_called_once()
        na.assert_called()

    def test_disable_disabled(self):
        node = MagicMock(spec=Node, enabled=False)
        with patch('vm.models.node.node_activity') as nac:
            na = MagicMock()
            na.__enter__.side_effect = AssertionError
            nac.return_value = na
            Node.disable(node)
        self.assertFalse(node.enabled)

    def test_disable_enabled_sub(self):
        node = MagicMock(spec=Node, enabled=True)
        act = MagicMock()
        subact = MagicMock()
        act.sub_activity.return_value = subact
        Node.disable(node, base_activity=act)
        self.assertFalse(node.enabled)
        subact.__enter__.assert_called()

    def test_flush(self):
        insts = [MagicMock(spec=Instance, migrate=MagicMock()),
                 MagicMock(spec=Instance, migrate=MagicMock())]
        node = MagicMock(spec=Node, enabled=True)
        node.instance_set.all.return_value = insts
        user = MagicMock(spec=User)
        flush_op = FlushOperation(node)

        with patch.object(FlushOperation, 'create_activity') as create_act:
            act = create_act.return_value = MagicMock()

            flush_op(user=user)

            create_act.assert_called()
            node.disable.assert_called_with(user, act)
            for i in insts:
                i.migrate.assert_called()

    def test_flush_disabled_wo_user(self):
        insts = [MagicMock(spec=Instance, migrate=MagicMock()),
                 MagicMock(spec=Instance, migrate=MagicMock())]
        node = MagicMock(spec=Node, enabled=False)
        node.instance_set.all.return_value = insts
        flush_op = FlushOperation(node)

        with patch.object(FlushOperation, 'create_activity') as create_act:
            act = create_act.return_value = MagicMock()

            flush_op(system=True)

            create_act.assert_called()
            node.disable.assert_called_with(None, act)
            # ^ should be called, but real method no-ops if disabled
            for i in insts:
                i.migrate.assert_called()
