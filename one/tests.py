from django.test import TestCase
from django.contrib.auth.models import User
from models import Disk, Instance, InstanceType, Network, Template, UserCloudDetails

class ViewsTestCase(TestCase):
    def test_index(self):
        '''Test whether index is reachable.'''
        resp = self.client.get('/', follow=True)
        self.assertEqual(resp.status_code, 200)

class UserCloudDetailsTestCase(TestCase):
    def setUp(self):
        user = User.objects.create(username="testuser",
                password="testpass", email="test@mail.com",
                first_name="Test", last_name="User")
        disk1 = Disk.objects.create(name="testdsk1")
        insttype = InstanceType.objects.create(name="testtype", CPU=4,
                RAM=4096, credit=4)
        ntwrk = Network.objects.create(name="testntwrk", nat=False,
                public=True)
        tmplt1 = Template.objects.create(name="testtmplt1", disk=disk1,
                instance_type=insttype, network=ntwrk, owner=user)
        tmplt2 = Template.objects.create(name="testtmplt2", disk=disk1,
                instance_type=insttype, network=ntwrk, owner=user)
        self.testinst1 = Instance.objects.create(owner=user, template=tmplt1,
                state="ACTIVE")
        self.testinst2 = Instance.objects.create(owner=user, template=tmplt2,
                state="ACTIVE")
        self.testdetails = UserCloudDetails.objects.get(user=user)

    def test_get_weighted_instance_count(self):
        credits = (self.testinst1.template.instance_type.credit +
                self.testinst2.template.instance_type.credit)
        self.assertEqual(credits, self.testdetails
                .get_weighted_instance_count())
        self.testinst1.state = "STOPPED"
        self.testinst1.save()
        self.assertEqual(self.testinst2.template.instance_type.credit,
                self.testdetails.get_weighted_instance_count())
        self.testinst2.state = "STOPPED"
        self.testinst2.save()
        self.assertEqual(0, self.testdetails.get_weighted_instance_count())
