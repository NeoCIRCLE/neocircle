from django.test import TestCase

from mock import Mock

from ..models import (
    InstanceTemplate, Instance, pre_state_changed, post_state_changed
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
