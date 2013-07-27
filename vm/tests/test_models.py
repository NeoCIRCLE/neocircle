from django.test import TestCase
from .models import Template


class TemplateTestCase(TestCase):
    def test_template_creation(self):
        template = Template(name='My first template',
                            access_method='ssh', )  # TODO add images & net
