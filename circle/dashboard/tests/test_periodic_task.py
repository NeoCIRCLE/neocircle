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

import unittest
from mock import patch, MagicMock

from django.contrib.auth.models import User

from ..models import Notification
from ..tasks import local_periodic_tasks


@patch.object(local_periodic_tasks, 'send_mail')
@patch.object(Notification, 'objects')
class EmailNotificationTestCase(unittest.TestCase):

    nextpk = 0

    def get_fake_notification(self, user=None, **kwargs):
        self.nextpk += 1
        if user is None:
            user = MagicMock(spec=User, pk=self.nextpk)
            user.profile.__unicode__.return_value = "user"
            user.email = "mail"
            user.profile.email_notifications = True
            user.profile.preferred_language = "en"
        params = {"to": user, "subject": "subj", "message": "msg",
                  "status": Notification.STATUS.new}
        params.update(kwargs)
        return MagicMock(spec=Notification, **params)

    def test_not_sending(self, no, sm):
        fake = [self.get_fake_notification()]
        fake[0].to.profile.email_notifications = False
        no.filter.return_value = fake
        local_periodic_tasks.send_email_notifications()
        assert not sm.called

    def test_sending(self, no, sm):
        fake = [self.get_fake_notification()]
        no.filter.return_value = fake
        local_periodic_tasks.send_email_notifications()
        assert sm.called
        assert all(i.status == i.STATUS.delivered for i in fake)

    def test_sending_more(self, no, sm):
        fake = [self.get_fake_notification(), self.get_fake_notification()]
        fake.append(self.get_fake_notification(fake[0].to))
        no.filter.return_value = fake
        local_periodic_tasks.send_email_notifications()
        self.assertEquals(sm.call_count, 2)
        assert all(i.status == i.STATUS.delivered for i in fake)

    def test_sending_some(self, no, sm):
        fake = [self.get_fake_notification(), self.get_fake_notification()]
        fake.append(self.get_fake_notification(fake[0].to))
        fake[1].to.profile.email_notifications = False
        no.filter.return_value = fake
        local_periodic_tasks.send_email_notifications()
        self.assertEquals(
            [i.status == i.STATUS.delivered for i in fake],
            [True, False, True])
        self.assertEquals(sm.call_count, 1)
