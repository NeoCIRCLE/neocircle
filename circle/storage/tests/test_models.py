from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from ..models import Disk, DataStore

old = timezone.now() - timedelta(days=2)
new = timezone.now() - timedelta(hours=2)


class DiskTestCase(TestCase):

    n = 0

    def setUp(self):
        self.ds = DataStore.objects.create(path="/datastore",
                                           hostname="devenv", name="default")

    def _disk(self, destroyed=None, base=None):
        self.n += 1
        n = "d%d" % self.n
        return Disk.objects.create(name=n, filename=n, base=base, size=1,
                                   destroyed=destroyed, datastore=self.ds)

    def test_deletable_not_destroyed(self):
        d = self._disk()
        assert not d.is_deletable

    def test_deletable_newly_destroyed(self):
        d = self._disk(destroyed=new)
        assert not d.is_deletable

    def test_deletable_no_child(self):
        d = self._disk(destroyed=old)
        assert d.is_deletable

    def test_deletable_child_not_destroyed(self):
        d = self._disk()
        self._disk(base=d, destroyed=old)
        self._disk(base=d)
        assert not d.is_deletable

    def test_deletable_child_newly_destroyed(self):
        d = self._disk(destroyed=old)
        self._disk(base=d, destroyed=new)
        self._disk(base=d)
        assert not d.is_deletable
