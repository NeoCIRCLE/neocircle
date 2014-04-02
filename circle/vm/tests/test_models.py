from datetime import datetime
from mock import Mock, MagicMock, patch, call

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
        inst = Mock(state='RUNNING')
        assert Instance.is_running.getter(inst)

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
        migrate_op = MigrateOperation(inst)
        with patch('vm.models.instance.vm_tasks.migrate') as migr:
            inst.select_node.side_effect = AssertionError
            act = MagicMock()
            with patch.object(MigrateOperation, 'create_activity',
                              return_value=act):
                migrate_op(to_node=inst.node, system=True)

            migr.apply_async.assert_called()
            self.assertNotIn(call.sub_activity(u'scheduling'), act.mock_calls)

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
            InstanceActivity.create("test", instance, concurrency_check=True)

    def test_create_no_concurrency_check(self):
        instance = MagicMock(spec=Instance)
        instance.activity_log.filter.return_value.exists.return_value = True

        original_method = InstanceActivity.create.__func__

        with patch('vm.models.activity.InstanceActivity') as ia, \
                patch('vm.models.activity.timezone.now'):
            # ia.__init__ = MagicMock()  raises AttributeError

            original_method(ia, "test", instance, concurrency_check=False)
            ia.save.assert_called()

            # ia.__init__.assert_called_with(activity_code='vm.Instance.test',
            #                                instance=instance, parent=None,
            #                                resultant_state=None, started=now,
            #                                task_uuid=None, user=None)

    def test_create_sub_concurrency_check(self):
        iaobj = MagicMock(spec=InstanceActivity)
        iaobj.children.filter.return_value.exists.return_value = True

        with self.assertRaises(ActivityInProgressError):
            InstanceActivity.create_sub(iaobj, "test", concurrency_check=True)

    def test_create_sub_no_concurrency_check(self):
        iaobj = MagicMock(spec=InstanceActivity)
        iaobj.activity_code = 'test'
        iaobj.children.filter.return_value.exists.return_value = True

        original_method = InstanceActivity.create_sub

        with patch('vm.models.activity.InstanceActivity') as ia, \
                patch('vm.models.activity.timezone.now'):
            original_method(iaobj, "test", concurrency_check=False)
            ia.save.assert_called()

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
