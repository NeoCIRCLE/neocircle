from django.test import TestCase

from ..models.instance import (
    InstanceTemplate, Instance
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
