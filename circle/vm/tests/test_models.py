from django.test import TestCase

from mock import Mock

from ..models.instance import (
    InstanceTemplate, Instance, pre_state_changed, post_state_changed
)
from ..models.network import (
    Interface
)
from ..models.common import (
    Lease
)


class TemplateTestCase(TestCase):

    def test_template_creation(self):
        template = InstanceTemplate(name='My first template',
                                    access_method='ssh', )
        template.clean()
        # TODO add images & net


class InstanceTestCase(TestCase):

    def test_pre_state_changed_w_exception(self):
        """Signal handler of pre_state_changed prevents save with Exception."""
        def callback(sender, new_state, **kwargs):
            if new_state == 'invalid value':
                raise Exception()
        pre_state_changed.connect(callback)
        i = Instance(state='NOSTATE')
        i.save = Mock()
        i.state_changed('invalid value')
        assert i.state == 'NOSTATE'
        assert not i.save.called

    def test_pre_state_changed_wo_exception(self):
        """Signal handler of pre_state_changed allows save."""
        mock = Mock()
        pre_state_changed.connect(mock)
        i = Instance(state='NOSTATE')
        i.save = Mock()
        i.state_changed('RUNNING')
        assert i.state == 'RUNNING'
        assert mock.called
        assert i.save.called

    def test_post_state_changed(self):
        """Signal handler of post_state_changed runs."""
        mock = Mock()
        post_state_changed.connect(mock)
        i = Instance(state='NOSTATE')
        i.save = Mock()
        i.state_changed('RUNNING')
        assert mock.called
        assert i.save.called
        assert i.state == 'RUNNING'


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
