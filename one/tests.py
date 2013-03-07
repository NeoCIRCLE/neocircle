from django.test import TestCase

class ViewsTestCase(TestCase):
    def test_index(self):
        '''Test whether index is reachable.'''
        resp = self.client.get('/', follow=True)
        self.assertEqual(resp.status_code, 200)
