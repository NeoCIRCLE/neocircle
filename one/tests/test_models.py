from datetime import datetime, timedelta
from django.test import TestCase
from django.contrib.auth.models import User
from ..models import Disk, Instance, InstanceType, Network, Share, Template
from school.models import Course, Group, Semester


class UserCloudDetailsTestCase(TestCase):
    def setUp(self):
        user = User.objects.create(username="testuser", password="testpass",
                                   email="test@mail.com", first_name="Test",
                                   last_name="User")
        disk1 = Disk.objects.create(name="testdsk1")
        insttype = InstanceType.objects.create(name="testtype", CPU=4,
                                               RAM=4096, credit=4)
        ntwrk = Network.objects.create(name="testntwrk", nat=False,
                                       public=True)
        tmplt1 = Template.objects.create(name="testtmplt1", disk=disk1,
                                         instance_type=insttype, owner=user,
                                         network=ntwrk)
        tmplt2 = Template.objects.create(name="testtmplt2", disk=disk1,
                                         instance_type=insttype, owner=user,
                                         network=ntwrk)
        self.testinst1 = Instance.objects.create(owner=user, state="ACTIVE",
                                                 template=tmplt1)
        self.testinst2 = Instance.objects.create(owner=user, state="ACTIVE",
                                                 template=tmplt2)
        self.userdetails = user.cloud_details
        date = datetime.now().date()
        delta = timedelta(weeks=7)
        sem = Semester.objects.create(name="testsem", start=date-delta,
                                      end=date+delta)
        course1 = Course.objects.create(code='tccode1', name='testcourse1',
                                        short_name='tc1')
        grp1 = Group.objects.create(name="testgroup1", semester=sem,
                                    course=course1)
        self.share1 = Share.objects.create(name="testshare1", group=grp1,
                                           template=tmplt1, owner=user,
                                           instance_limit=2,
                                           per_user_limit=1)

    def test_reset_keys(self):
        private_key = self.userdetails.ssh_private_key
        public_key = self.userdetails.ssh_key.key
        self.userdetails.reset_keys()
        self.assertIsNotNone(self.userdetails.ssh_private_key)
        self.assertNotEqual(private_key, self.userdetails.ssh_private_key)
        self.assertIsNotNone(self.userdetails.ssh_key.key)
        self.assertNotEqual(public_key, self.userdetails.ssh_key.key)

    def test_reset_keys_without_key(self):
        private_key = self.userdetails.ssh_private_key
        self.userdetails.ssh_key = None
        self.userdetails.save()
        self.userdetails.reset_keys()
        self.assertIsNotNone(self.userdetails.ssh_private_key)
        self.assertNotEqual(private_key, self.userdetails.ssh_private_key)
        self.assertIsNotNone(self.userdetails.ssh_key)

    def test_reset_smb(self):
        smb_password = self.userdetails.smb_password
        self.userdetails.reset_smb()
        self.assertIsNotNone(self.userdetails.smb_password)
        self.assertNotEqual(smb_password, self.userdetails.smb_password)

    def test_get_weighted_instance_count(self):
        credits = (self.testinst1.template.instance_type.credit +
                   self.testinst2.template.instance_type.credit)
        self.assertEqual(credits,
                         self.userdetails.get_weighted_instance_count())
        self.testinst1.state = "STOPPED"
        self.testinst1.save()
        self.assertEqual(self.testinst2.template.instance_type.credit,
                         self.userdetails.get_weighted_instance_count())
        self.testinst2.state = "STOPPED"
        self.testinst2.save()
        self.assertEqual(0, self.userdetails.get_weighted_instance_count())

    def test_get_instance_pc(self):
        instance_pc = self.userdetails.get_instance_pc()
        self.assertTrue(instance_pc >= 0)

    def test_get_instance_pc_with_zero_instance_quota(self):
        self.userdetails.instance_quota = 0
        self.userdetails.save()
        self.assertEqual(100, self.userdetails.get_instance_pc())

    def test_get_weighted_share_count(self):
        share = self.share1
        count = share.template.instance_type.credit * share.instance_limit
        self.assertEqual(count, self.userdetails.get_weighted_share_count())

    def test_get_share_pc(self):
        self.userdetails.share_quota = 50
        share_pc = self.userdetails.get_share_pc()
        self.assertTrue(share_pc >= 0)

    def test_get_share_pc_with_zero_share_quota(self):
        self.userdetails.share_quota = 0
        self.userdetails.save()
        self.assertEqual(100, self.userdetails.get_share_pc())
