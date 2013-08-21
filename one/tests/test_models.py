from datetime import datetime, timedelta
from mock import Mock, patch
from nose import with_setup
from nose.tools import raises
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from ..models import (Disk, Instance, InstanceType, Network, Share,
                      Template, set_quota, reset_keys, OpenSshKeyValidator)
from ..util import keygen
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
        sem = Semester.objects.create(name="testsem", start=date - delta,
                                      end=date + delta)
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


def create_user():
    return User.objects.create(username="testuser", password="testpass",
                               email="test@mail.com", first_name="Test",
                               last_name="User")


def delete_user():
    User.objects.filter(username="testuser").delete()


@with_setup(create_user, delete_user)
@patch('one.models.StoreApi')
def test_set_quota(MockStoreApi):
    MockStoreApi.userexist = Mock(return_value=True)
    MockStoreApi.set_quota = Mock()
    user = User.objects.get(username="testuser")
    details = user.cloud_details
    set_quota(None, details, None)
    MockStoreApi.userexist.assert_called_once_with(user.username)
    MockStoreApi.set_quota.assert_called_once_with(user.username,
                                                   details.disk_quota * 1024)


@with_setup(create_user, delete_user)
@patch('one.models.StoreApi')
def test_set_quota_without_store_user(MockStoreApi):
    MockStoreApi.userexist = Mock(return_value=False)
    MockStoreApi.createuser = Mock()
    user = User.objects.get(username="testuser")
    details = user.cloud_details
    set_quota(None, details, None)
    MockStoreApi.userexist.assert_called_once_with(user.username)
    assert MockStoreApi.createuser.called
    assert MockStoreApi.createuser.call_count == 1


@with_setup(create_user, delete_user)
def test_reset_keys_when_created():
    mock_details = Mock()
    mock_details.reset_smb = Mock(return_value=None)
    mock_details.reset_ssh_keys = Mock(return_value=None)
    reset_keys(None, mock_details, True)
    mock_details.reset_smb.assert_called_once_with()
    mock_details.reset_ssh_keys.assert_called_once_with()


@with_setup(create_user, delete_user)
def test_reset_keys_when_not_created():
    mock_details = Mock()
    mock_details.reset_smb = Mock(return_value=None)
    mock_details.reset_ssh_keys = Mock(return_value=None)
    reset_keys(None, mock_details, False)
    assert not mock_details.reset_smb.called
    assert not mock_details.reset_ssh_keys.called


def test_OpenSshKeyValidator_init_with_types():
    key_types = ['my-key-type']
    validator = OpenSshKeyValidator(types=key_types)
    assert validator.valid_types == key_types


def test_OpenSshKeyValidator_with_valid_key():
    validator = OpenSshKeyValidator()
    _, public_key = keygen()
    validator(public_key)


@raises(ValidationError)
def test_OpenSshKeyValidator_with_empty_string_as_key():
    validator = OpenSshKeyValidator()
    public_key = ""
    validator(public_key)


@raises(ValidationError)
def test_OpenSshKeyValidator_with_invalid_key_type():
    validator = OpenSshKeyValidator()
    _, public_key = keygen()
    _key_type, rest = public_key.split(None, 1)
    public_key = 'my-key-type ' + rest
    validator(public_key)


@raises(ValidationError)
def test_OpenSshKeyValidator_with_invalid_key_data():
    validator = OpenSshKeyValidator()
    _, public_key = keygen()
    key_parts = public_key.split(None, 2)
    key_parts[1] = key_parts[1][1:]
    public_key = ' '.join(key_parts)
    validator(public_key)


def test_Share_extend_type():
    t = {'delete': timedelta(weeks=2), 'suspend': timedelta(weeks=1)}
    Share.extend_type(t)
    assert 'deletex' in t
    assert 'suspendx' in t
    assert t['deletex'] is not None
    assert t['suspendx'] is not None


def test_Share_extend_type_with_no_deletion_interval():
    t = {'delete': None, 'suspend': timedelta(weeks=1)}
    Share.extend_type(t)
    assert 'deletex' in t
    assert 'suspendx' in t
    assert t['deletex'] is None
    assert t['suspendx'] is not None


def test_Share_extend_type_with_no_suspension_interval():
    t = {'delete': timedelta(weeks=2), 'suspend': None}
    Share.extend_type(t)
    assert 'deletex' in t
    assert 'suspendx' in t
    assert t['deletex'] is not None
    assert t['suspendx'] is None
