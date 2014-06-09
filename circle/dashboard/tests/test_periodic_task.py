import unittest
from mock import patch, MagicMock


from ..models import Notification
from ..tasks import local_periodic_tasks


@patch.object(local_periodic_tasks, 'send_mail')
@patch.object(Notification, 'objects')
class EmailNotificationTestCase(unittest.TestCase):
    def test_not_sending(self, no, sm):
        fake = MagicMock(spec=Notification)
        fake.to.profile.email_notifications = False
        no.filter.return_value = [fake]
        local_periodic_tasks.send_email_notifications()
        assert not sm.called

    def test_sending(self, no, sm):
        fake = MagicMock(spec=Notification)
        fake.to.profile.__unicode__.return_value = "user"
        fake.to.email = "mail"
        fake.to.profile.email_notifications = True
        fake.to.profile.preferred_language = "en"
        fake.subject = "subj"
        fake.message = "msg"
        no.filter.return_value = [fake]
        local_periodic_tasks.send_email_notifications()
        assert sm.called
        assert fake.status == fake.STATUS.delivered
