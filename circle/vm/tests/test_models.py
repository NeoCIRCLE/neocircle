from django.test import TestCase
from ..models import InstanceTemplate


class TemplateTestCase(TestCase):
    def test_template_creation(self):
        template = InstanceTemplate(name='My first template',
                                    access_method='ssh', )
        # TODO add images & net
