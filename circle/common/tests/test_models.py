from collections import deque

from django.test import TestCase
from mock import MagicMock

from .models import TestClass
from ..models import HumanSortField


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


class TestHumanSortField(TestCase):

    def test_partition(self):
        values = {(lambda s: s.isdigit(), "1234abc56"): ("1234", "abc", "56"),
                  (lambda s: s.isalpha(), "abc567"): ("abc", "567", ""),
                  (lambda s: s == "a", "aaababaa"): ("aaa", "b", "abaa"),
                  (lambda s: s == "a", u"aaababaa"): ("aaa", "b", "abaa"),
                  }
        for (pred, val), result in values.iteritems():
            a, b, c = HumanSortField._partition(deque(val), pred)
            assert isinstance(c, deque)
            c = ''.join(c)
            # print "%s, %s => %s" % (val, str(pred), str((a, b, c)))
            self.assertEquals((a, b, c), result)

    def test_get_normalized(self):
        values = {("1234abc56", 4): "1234abc0056",
                  ("abc567", 2): "abc567",
                  ("aaababaa", 8): "aaababaa",
                  ("aa4ababaa", 2): "aa04ababaa",
                  ("aa4aba24baa4", 4): "aa0004aba0024baa0004",
                  }
        for (val, length), result in values.iteritems():
            obj = MagicMock(spec=HumanSortField, maximum_number_length=length,
                            _partition=HumanSortField._partition)

            test_result = HumanSortField.get_normalized_value(obj, val)
            self.assertEquals(test_result, result)
