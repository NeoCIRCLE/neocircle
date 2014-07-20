# Copyright 2014 Budapest University of Technology and Economics (BME IK)
#
# This file is part of CIRCLE Cloud.
#
# CIRCLE is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# CIRCLE is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along
# with CIRCLE.  If not, see <http://www.gnu.org/licenses/>.

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
                             '%(var)s %(user)s',
                             {'var': 'testme'})
        assert self.u1.notification_set.count() == c1 + 1
        assert self.u2.notification_set.count() == c2
        assert 'user1' in unicode(msg.message)
        assert 'testme' in unicode(msg.message)
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
