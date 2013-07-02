from django.core.urlresolvers import reverse
from django.test import TestCase

class ViewsTestCase(TestCase):
    def test_index(self):
        '''Test whether index is reachable.'''
        url = reverse('one.views.index')
        resp = self.client.get(url, follow=True)
        self.assertEqual(resp.status_code, 200)
