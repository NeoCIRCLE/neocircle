from datetime import datetime
from django.test import TestCase
from django.utils.translation import ugettext_lazy as _
from mock import Mock, MagicMock, patch

from ..models import (
    Lease, Node, Interface, Instance, InstanceTemplate,
)
from ..models.instance import find_unused_port


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

    def test_deploy_destroyed(self):
        inst = Mock(destroyed_at=datetime.now(), spec=Instance,
                    InstanceDestroyedError=Instance.InstanceDestroyedError)
        with self.assertRaises(Instance.InstanceDestroyedError):
            Instance.deploy(inst)

    def test_destroy_destroyed(self):
        inst = Mock(destroyed_at=datetime.now(), spec=Instance)
        Instance.destroy(inst)
        self.assertFalse(inst.save.called)

    def test_destroy_sets_destroyed(self):
        inst = MagicMock(destroyed_at=None, spec=Instance)
        inst.node = MagicMock(spec=Node)
        inst.disks.all.return_value = []
        with patch('vm.models.instance.instance_activity') as ia:
            ia.return_value = MagicMock()
            Instance.destroy(inst)
        self.assertTrue(inst.destroyed_at)
        inst.save.assert_called()


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


class NodeTestCase(TestCase):

    def test_state(self):
        node = Mock(spec=Node)
        node.online = True
        node.enabled = True
        node.STATES = Node.STATES
        self.assertEqual(Node.get_state(node), "ONLINE")
        assert isinstance(Node.get_status_display(node), _("").__class__)
