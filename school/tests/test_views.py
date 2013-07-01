from datetime import datetime, timedelta
from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User, Group as AuthGroup
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.utils.datastructures import MultiValueDictKeyError
from ..models import create_user_profile, Person, Course, Semester, Group
from one.models import (UserCloudDetails, Disk, InstanceType, Network,
        Template)
import json

class ViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        date = datetime.now().date()
        delta = timedelta(weeks=7)
        self.semester = Semester.objects.create(name="testsem",
                start=date-delta, end=date+delta)
        course1 = Course.objects.create(code='tccode1',
                name='testcourse1', short_name='tc1')
        course2 = Course.objects.create(code='tccode2',
                name='testcourse2', short_name='tc2')
        nonexistent_course_code1 = 'vacationspotscouting'
        nonexistent_course_code2 = 'caringforunicorns'
        affiliation1 = AuthGroup.objects.create(name='chalktrademanager')
        self.group1 = Group.objects.create(name=affiliation1.name,
                semester=self.semester, course=course1)
        self.http_headers = {
            'niifPersonOrgID': 'ABUZER',
            'niifEduPersonHeldCourse': ';'.join(
                [course1.code, nonexistent_course_code1]),
            'niifEduPersonAttendedCourse': ';'.join(
                [course2.code, nonexistent_course_code2]),
            'givenName': 'Test',
            'sn': 'User',
            'email': 'test.user@testsite.hu',
            'affiliation': ';'.join([affiliation1.name])}


    def login(self, follow=False):
        url = reverse('login')
        resp = self.client.get(url, follow=follow, **self.http_headers)
        try:
            username = self.http_headers['niifPersonOrgID']
            self.user = User.objects.get(username=username)
        except KeyError:
            pass
        except User.DoesNotExist:
            pass
        return resp


    #
    # school.views.logout
    #
    def test_logout(self):
        resp = self.client.get(reverse('logout'), follow=False)
        self.assertEqual(302, resp.status_code)


    #
    # school.views.login
    #
    def test_login(self):
        resp = self.login(follow=True)
        self.assertEqual(200, resp.status_code)


    def test_login_without_id(self):
        del self.http_headers['niifPersonOrgID']
        resp = self.login(follow=True)
        self.assertEqual(200, resp.status_code)
        (url, _) = resp.redirect_chain[0]
        self.assertIn('/admin', url)


    def test_login_without_email(self):
        del self.http_headers['email']
        resp = self.login(follow=True)
        self.assertEqual(403, resp.status_code)


    def test_login_without_affiliation(self):
        del self.http_headers['affiliation']
        resp = self.login(follow=True)
        self.assertEqual(200, resp.status_code)


    def test_login_without_group_for_affiliation(self):
        self.group1.delete()
        resp = self.login(follow=True)
        self.assertEqual(200, resp.status_code)


    #
    # school.views.language
    #
    def test_language(self):
        self.login()
        p = Person.objects.get(user=self.user)
        lang = u'en' if p.language == u'hu' else u'hu'
        url = reverse('school.views.language', kwargs={'lang': lang})
        self.http_headers['HTTP_REFERER'] = '/'
        resp = self.client.get(url, follow=False, **self.http_headers)
        self.assertEqual(302, resp.status_code)
        p = Person.objects.get(user=self.user)
        self.assertEqual(lang, p.language)


    def test_language_with_invalid_parameter(self):
        self.login()
        lang_before = Person.objects.get(user=self.user).language
        invalid_lang = u'nemvanez'
        url = reverse('school.views.language', kwargs={'lang': invalid_lang})
        self.http_headers['HTTP_REFERER'] = '/'
        resp = self.client.get(url, follow=False, **self.http_headers)
        self.assertEqual(302, resp.status_code)
        p = Person.objects.get(user=self.user)
        self.assertEqual(lang_before, p.language) # language didn't change


    def test_language_without_person_for_user(self):
        self.login()
        Person.objects.get(user=self.user).delete()
        new_lang = u'en'
        url = reverse('school.views.language', kwargs={'lang': new_lang})
        self.http_headers['HTTP_REFERER'] = '/'
        resp = self.client.get(url, follow=False, **self.http_headers)
        self.assertEqual(302, resp.status_code)


    #
    # school.views.group_show
    #
    def test_group_show(self):
        self.login()
        ucd = UserCloudDetails.objects.get(user=self.user)
        ucd.share_quota = 10
        ucd.save()
        disk = Disk.objects.create(name="testdsk1")
        insttype = InstanceType.objects.create(name="testtype", CPU=4,
                RAM=4096, credit=4)
        ntwrk = Network.objects.create(name="testntwrk", nat=False,
                public=True)
        tmplt = Template.objects.create(name="testtmplt1", disk=disk,
                instance_type=insttype, network=ntwrk, owner=self.user,
                state='READY')
        gid = self.group1.id
        url = reverse('school.views.group_show', kwargs={'gid': gid})
        resp = self.client.get(url)
        self.assertEqual(200, resp.status_code)


    def test_group_show_with_nonexistent_group_id(self):
        self.login()
        gid = 1337  # this should be the ID of a non-existent group,
        Group.objects.filter(id=gid).delete()  # so if it exists, delete it!
        url = reverse('school.views.group_show', kwargs={'gid': gid})
        resp = self.client.get(url)
        self.assertEqual(404, resp.status_code)


    #
    # school.views.group_new
    #
    def test_group_new(self):
        self.login()
        url = reverse('school.views.group_new')
        member1 = Person.objects.create(code="A1B2C3")
        members = [member1]
        data = {
                'name': 'myNewGrp',
                'semester': Semester.get_current().id,
                'members': '\n'.join([m.code for m in members]),
                }
        resp = self.client.post(url, data)
        group = Group.objects.get(name=data['name'])
        self.assertEqual(Semester.get_current(), group.semester)
        for member in members:
            self.assertIn(member, group.members.all())


    def test_group_new_without_members(self):
        self.login()
        url = reverse('school.views.group_new')
        data = {
                'name': 'myNewGrp',
                'semester': Semester.get_current().id,
                'members': '',
                }
        resp = self.client.post(url, data)
        group = Group.objects.get(name=data['name'])
        self.assertEqual(Semester.get_current(), group.semester)
        self.assertFalse(group.members.exists())


    def test_group_new_with_invalid_neptun(self):
        self.login()
        url = reverse('school.views.group_new')
        data = {
                'name': 'myNewGrp',
                'semester': Semester.get_current().id,
                'members': '1ABC123',  # invalid neptun
                }
        resp = self.client.post(url, data)
        self.assertFalse(Group.objects.filter(name=data['name']).exists())


    #
    # school.views.group_ajax_add_new_member
    #
    def test_group_ajax_add_new_member(self):
        self.login()
        group = Group.objects.create(name="mytestgroup",
                semester=Semester.get_current())
        url = reverse('school.views.group_ajax_add_new_member',
                kwargs={'gid': group.id})
        new_member = Person.objects.get(user=self.user)
        data = {'neptun': new_member.code}
        resp = self.client.post(url, data)
        self.assertEqual(200, resp.status_code)
        group = Group.objects.get(id=group.id)
        self.assertIn(new_member, group.members.all())


    def test_group_ajax_add_new_member_with_nonexistent_group_id(self):
        self.login()
        gid = 1337  # this should be the ID of a non-existent group,
        Group.objects.filter(id=gid).delete()  # so if it exists, delete it!
        url = reverse('school.views.group_ajax_add_new_member',
                kwargs={'gid': gid})
        new_member = Person.objects.get(user=self.user)
        data = {'neptun': new_member.code}
        resp = self.client.post(url, data)
        self.assertEqual(404, resp.status_code)


    def test_group_ajax_add_new_member_without_neptun(self):
        self.login()
        group = Group.objects.create(name="mytestgroup",
                semester=Semester.get_current())
        url = reverse('school.views.group_ajax_add_new_member',
                kwargs={'gid': group.id})
        new_member = Person.objects.get(user=self.user)
        data = {}
        with self.assertRaises(MultiValueDictKeyError):
            self.client.post(url, data)
        group = Group.objects.get(id=group.id)
        self.assertNotIn(new_member, group.members.all())


    def test_group_ajax_add_new_member_with_invalid_neptun(self):
        self.login()
        group = Group.objects.create(name="mytestgroup",
                semester=Semester.get_current())
        url = reverse('school.views.group_ajax_add_new_member',
                kwargs={'gid': group.id})
        new_member = Person.objects.get(user=self.user)
        self.assertNotIn(new_member, group.members.all())
        data = {'neptun': '1' + new_member.code}
        resp = self.client.post(url, data)
        self.assertEqual(200, resp.status_code)
        content = json.loads(resp.content)
        self.assertEqual('Error', content['status'])
        group = Group.objects.get(id=group.id)
        self.assertNotIn(new_member, group.members.all())


    def test_group_ajax_add_new_member_with_nonexistent_member(self):
        self.login()
        group = Group.objects.create(name="mytestgroup",
                semester=Semester.get_current())
        url = reverse('school.views.group_ajax_add_new_member',
                kwargs={'gid': group.id})
        new_member_code = 'ZXY012'  # this should be the ID of a
                                    # non-existent person, so if it exists,
        Person.objects.filter(code=new_member_code).delete()  # delete it!
        data = {'neptun': new_member_code}
        resp = self.client.post(url, data)
        self.assertEqual(200, resp.status_code)
        self.assertTrue(Person.objects.filter(code=new_member_code))
        new_member = Person.objects.get(code=new_member_code)
        group = Group.objects.get(id=group.id)
        self.assertIn(new_member, group.members.all())


    #
    # school.views.group_ajax_remove_member
    #
    def test_group_ajax_remove_member(self):
        self.login()
        group = Group.objects.create(name="mytestgroup",
                semester=Semester.get_current())
        member = Person.objects.get(user=self.user)
        group.members.add(member)
        group.save()
        url = reverse('school.views.group_ajax_remove_member',
                kwargs={'gid': group.id})
        data = {'neptun': member.code}
        resp = self.client.post(url, data)
        self.assertEqual(200, resp.status_code)
        group = Group.objects.get(id=group.id)
        self.assertNotIn(member, group.members.all())


    def test_group_ajax_remove_member_with_nonexistent_group_id(self):
        self.login()
        gid = 1337  # this should be the ID of a non-existent group,
        Group.objects.filter(id=gid).delete()  # so if it exists, delete it!
        member = Person.objects.get(user=self.user)
        url = reverse('school.views.group_ajax_remove_member',
                kwargs={'gid': gid})
        data = {'neptun': member.code}
        resp = self.client.post(url, data)
        self.assertEqual(404, resp.status_code)


    def test_group_ajax_remove_member_without_neptun(self):
        self.login()
        group = Group.objects.create(name="mytestgroup",
                semester=Semester.get_current())
        member = Person.objects.get(user=self.user)
        group.members.add(member)
        group.save()
        url = reverse('school.views.group_ajax_remove_member',
                kwargs={'gid': group.id})
        data = {}
        with self.assertRaises(MultiValueDictKeyError):
            self.client.post(url, data)
        group = Group.objects.get(id=group.id)
        self.assertIn(member, group.members.all())


    def test_group_ajax_remove_member_with_invalid_neptun(self):
        self.login()
        group = Group.objects.create(name="mytestgroup",
                semester=Semester.get_current())
        member = Person.objects.get(user=self.user)
        group.members.add(member)
        group.save()
        url = reverse('school.views.group_ajax_remove_member',
                kwargs={'gid': group.id})
        data = {'neptun': '1' + member.code}  # invalid Neptun code
        resp = self.client.post(url, data)
        self.assertEqual(200, resp.status_code)
        content = json.loads(resp.content)
        self.assertEqual('Error', content['status'])
        group = Group.objects.get(id=group.id)
        self.assertIn(member, group.members.all())


    def test_group_ajax_remove_member_with_nonexistent_member(self):
        self.login()
        group = Group.objects.create(name="mytestgroup",
                semester=Semester.get_current())
        member_code = 'ZXY012'  # this should be the ID of a non-existent
                                # person, so if it exists,
        Person.objects.filter(code=member_code).delete()  # delete it!
        url = reverse('school.views.group_ajax_remove_member',
                kwargs={'gid': group.id})
        data = {'neptun': member_code}
        with self.assertRaises(Person.DoesNotExist):
            self.client.post(url, data)
        self.assertFalse(Person.objects.filter(code=member_code).exists())


    #
    # school.views.group_ajax_delete
    #
    def test_group_ajax_delete(self):
        self.login()
        group = Group.objects.create(name="mytestgroup",
                semester=Semester.get_current())
        url = reverse('school.views.group_ajax_delete')
        data = {'gid': group.id}
        resp = self.client.post(url, data)
        self.assertEqual(200, resp.status_code)
        self.assertFalse(Group.objects.filter(id=group.id).exists())


    def test_group_ajax_delete_without_gid(self):
        self.login()
        url = reverse('school.views.group_ajax_delete')
        data = {}
        with self.assertRaises(MultiValueDictKeyError):
            self.client.post(url, data)


    def test_group_ajax_delete_with_nonexistent_group_id(self):
        self.login()
        gid = 1337  # this should be the ID of a non-existent group,
        Group.objects.filter(id=gid).delete()  # so if it exists, delete it!
        url = reverse('school.views.group_ajax_delete')
        data = {'gid': gid}
        resp = self.client.post(url, data)
        self.assertEqual(404, resp.status_code)


    #
    # school.views.group_ajax_owner_autocomplete
    #
    def test_group_ajax_owner_autocomplete(self):
        self.login()
        query = self.user.last_name[:2]
        url = reverse('school.views.group_ajax_owner_autocomplete')
        data = {'q': query}
        resp = self.client.post(url, data)
        self.assertEqual(200, resp.status_code)
        content = json.loads(resp.content)
        user_data = {'name': self.user.get_full_name(),
                     'neptun': self.user.username}
        self.assertIn(user_data, content)


    def test_group_ajax_owner_autocomplete_without_query(self):
        self.login()
        url = reverse('school.views.group_ajax_owner_autocomplete')
        data = {}
        with self.assertRaises(MultiValueDictKeyError):
            self.client.post(url, data)


    #
    # school.views.group_ajax_add_new_owner
    #
    def test_group_ajax_add_new_owner(self):
        self.login()
        user_details = UserCloudDetails.objects.get(user=self.user)
        user_details.share_quota = 10
        user_details.save()
        group = Group.objects.create(name="mytestgroup",
                semester=Semester.get_current())
        new_owner = Person.objects.get(code=self.user.username)
        self.assertNotIn(new_owner, group.owners.all())
        url = reverse('school.views.group_ajax_add_new_owner',
                kwargs={'gid': group.id})
        data = {'neptun': new_owner.code}
        resp = self.client.post(url, data)
        self.assertEqual(200, resp.status_code)
        content = json.loads(resp.content)
        self.assertEqual('OK', content['status'])
        group = Group.objects.get(id=group.id)
        self.assertIn(new_owner, group.owners.all())


    def test_group_ajax_add_new_owner_without_enough_share_quota(self):
        self.login()
        user_details = UserCloudDetails.objects.get(user=self.user)
        user_details.share_quota = 0
        user_details.save()
        group = Group.objects.create(name="mytestgroup",
                semester=Semester.get_current())
        new_owner = Person.objects.get(code=self.user.username)
        self.assertNotIn(new_owner, group.owners.all())
        url = reverse('school.views.group_ajax_add_new_owner',
                kwargs={'gid': group.id})
        data = {'neptun': new_owner.code}
        resp = self.client.post(url, data)
        self.assertEqual(200, resp.status_code)
        content = json.loads(resp.content)
        self.assertEqual('denied', content['status'])
        group = Group.objects.get(id=group.id)
        self.assertNotIn(new_owner, group.owners.all())


    def test_group_ajax_add_new_owner_with_nonexistent_group_id(self):
        self.login()
        user_details = UserCloudDetails.objects.get(user=self.user)
        user_details.share_quota = 10
        user_details.save()
        gid = 1337  # this should be the ID of a non-existent group,
        Group.objects.filter(id=gid).delete()  # so if it exists, delete it!
        new_owner = Person.objects.get(code=self.user.username)
        url = reverse('school.views.group_ajax_add_new_owner',
                kwargs={'gid': gid})
        data = {'neptun': new_owner.code}
        resp = self.client.post(url, data)
        self.assertEqual(404, resp.status_code)

    def test_group_ajax_add_new_owner_without_neptun(self):
        self.login()
        user_details = UserCloudDetails.objects.get(user=self.user)
        user_details.share_quota = 10
        user_details.save()
        group = Group.objects.create(name="mytestgroup",
                semester=Semester.get_current())
        new_owner = Person.objects.get(code=self.user.username)
        self.assertNotIn(new_owner, group.owners.all())
        url = reverse('school.views.group_ajax_add_new_owner',
                kwargs={'gid': group.id})
        data = {}
        with self.assertRaises(MultiValueDictKeyError):
            self.client.post(url, data)
        group = Group.objects.get(id=group.id)
        self.assertNotIn(new_owner, group.owners.all())


    def test_group_ajax_add_new_owner_with_invalid_neptun(self):
        self.login()
        user_details = UserCloudDetails.objects.get(user=self.user)
        user_details.share_quota = 10
        user_details.save()
        group = Group.objects.create(name="mytestgroup",
                semester=Semester.get_current())
        new_owner = Person.objects.get(code=self.user.username)
        self.assertNotIn(new_owner, group.owners.all())
        url = reverse('school.views.group_ajax_add_new_owner',
                kwargs={'gid': group.id})
        data = {'neptun': '1' + new_owner.code}
        resp = self.client.post(url, data)
        self.assertEqual(200, resp.status_code)
        content = json.loads(resp.content)
        self.assertEqual('Error', content['status'])
        group = Group.objects.get(id=group.id)
        self.assertNotIn(new_owner, group.owners.all())
