from django.contrib.auth.models import User

from django.test import TestCase

from ..models import Profile
from ..views import search_user


class NotificationTestCase(TestCase):

    def setUp(self):
        self.u1 = User.objects.create(username='user1')
        Profile.objects.get_or_create(user=self.u1)
        self.u2 = User.objects.create(username='user2')
        Profile.objects.get_or_create(user=self.u2)

    def test_notification_send(self):
        c1 = self.u1.notification_set.count()
        c2 = self.u2.notification_set.count()
        profile = self.u1.profile
        msg = profile.notify('subj',
                             'dashboard/test_message.txt',
                             {'var': 'testme'})
        assert self.u1.notification_set.count() == c1 + 1
        assert self.u2.notification_set.count() == c2
        assert 'user1' in msg.message
        assert 'testme' in msg.message
        assert msg in self.u1.notification_set.all()


class ProfileTestCase(TestCase):

    def setUp(self):
        self.u1 = User.objects.create(username='user1')
        Profile.objects.get_or_create(user=self.u1)
        self.u2 = User.objects.create(username='user2',
                                      email='john@example.org')
        Profile.objects.get_or_create(user=self.u2, org_id='apple')

    def test_search_user_by_name(self):
        self.assertEqual(search_user('user1'), self.u1)
        self.assertEqual(search_user('user2'), self.u2)

    def test_search_user_by_mail(self):
        self.assertEqual(search_user('john@example.org'), self.u2)

    def test_search_user_by_orgid(self):
        self.assertEqual(search_user('apple'), self.u2)

    def test_search_user_nonexist(self):
        with self.assertRaises(User.DoesNotExist):
            search_user('no-such-user')
