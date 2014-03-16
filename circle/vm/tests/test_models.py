from django.test import TestCase
from mock import Mock, MagicMock, patch, call

from ..models.common import (
    Lease
)
from ..models.instance import (
    find_unused_port, InstanceTemplate, Instance
)
from ..models.network import (
    Interface
)
from ..models.node import Node


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

    def test_migrate_with_scheduling(self):
        inst = MagicMock(spec=Instance)
        inst.interface_set.all.return_value = []
        inst.node = MagicMock(spec=Node)
        with patch('vm.models.instance.instance_activity') as ia, \
                patch('vm.models.instance.vm_tasks.migrate') as migr:
            Instance.migrate(inst)

            migr.apply_async.assert_called()
            self.assertIn(call().__enter__().sub_activity(u'scheduling'),
                          ia.mock_calls)
            inst.select_node.assert_called()

    def test_migrate_wo_scheduling(self):
        inst = MagicMock(spec=Instance)
        inst.interface_set.all.return_value = []
        inst.node = MagicMock(spec=Node)
        with patch('vm.models.instance.instance_activity') as ia, \
                patch('vm.models.instance.vm_tasks.migrate') as migr:
            inst.select_node.side_effect = AssertionError

            Instance.migrate(inst, inst.node)

            migr.apply_async.assert_called()
            self.assertNotIn(call().__enter__().sub_activity(u'scheduling'),
                             ia.mock_calls)


class InterfaceTestCase(TestCase):

    def test_interface_create(self):
        from firewall.models import Vlan, Domain
        from django.contrib.auth.models import User
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
