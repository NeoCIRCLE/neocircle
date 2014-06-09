import unittest
from mock import patch, MagicMock

from django.contrib.auth.models import User

from ..models import Notification
from ..tasks import local_periodic_tasks


@patch.object(local_periodic_tasks, 'send_mail')
@patch.object(Notification, 'objects')
class EmailNotificationTestCase(unittest.TestCase):
    def get_fake_notification(self, user=None, **kwargs):
        if user is None:
            user = MagicMock(spec=User)
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
