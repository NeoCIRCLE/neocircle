from django.test import TestCase
from .models import TestClass


class MethodCacheTestCase(TestCase):
    def test_cache(self):
        t1 = TestClass(1)
        t2 = TestClass(2)

        val1a = t1.method('a')
        val1b = t1.method('a')
        val2a = t2.method('a')
        val2b = t2.method('a')
        val2b = t2.method('a')

        self.assertEqual(val1a, val1b)
        self.assertEqual(val2a, val2b)
        self.assertNotEqual(val1a, val2a)

        t1.method('b')
        self.assertEqual(t1.called, 2)
        self.assertEqual(t2.called, 1)

    def test_invalidate(self):
        t1 = TestClass(1)
        val1a = t1.method('a')
        val1b = t1.method('a', invalidate_cache=True)
        t1.method('a')
        self.assertEqual(val1a, val1b)
        self.assertEqual(t1.called, 2)
