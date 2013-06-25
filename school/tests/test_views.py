from datetime import datetime, timedelta
from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User, Group as AuthGroup
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from ..models import create_user_profile, Person, Course, Semester, Group
from one.models import UserCloudDetails

class ViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        date = datetime.now().date()
        delta = timedelta(weeks=7)
        semester= Semester.objects.create(name="testsem", start=date-delta,
                    end=date+delta)
        course1 = Course.objects.create(code='tccode1',
                name='testcourse1', short_name='tc1')
        course2 = Course.objects.create(code='tccode2',
                name='testcourse2', short_name='tc2')
        nonexistent_course_code1 = 'vacationspotscouting'
        nonexistent_course_code2 = 'caringforunicorns'
        affiliation1 = AuthGroup.objects.create(name='chalktrademanager')
        self.group1 = Group.objects.create(name=affiliation1.name,
                semester=semester, course=course1)
        self.http_headers = {
            'niifPersonOrgID': 'ABUZER',
            'niifEduPersonHeldCourse': ';'.join(
                [course1.code, nonexistent_course_code1]),
            'niifEduPersonAttendedCourse': ';'.join(
                [course2.code, nonexistent_course_code2]),
            'givenName': 'User',
            'sn': 'Test',
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


    def test_logout(self):
        resp = self.client.get(reverse('logout'), follow=False)
        self.assertEqual(302, resp.status_code)


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
        new_lang = u'nemvanez' # invalid language
        url = reverse('school.views.language', kwargs={'lang': new_lang})
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


    def test_group_show(self):
        self.login()
        ucd = UserCloudDetails.objects.get(user=self.user)
        ucd.share_quota = 10
        ucd.save()
        gid = self.group1.id
        url = reverse('school.views.group_show', kwargs={'gid': gid})
        resp = self.client.get(url)
        self.assertEqual(200, resp.status_code)


    def test_group_show_with_nonexistent_groupid(self):
        self.login()
        gid = 1337  # this should be the ID of a non-existent group,
        Group.objects.filter(id=gid).delete()  # so if it exists, delete it!
        url = reverse('school.views.group_show', kwargs={'gid': gid})
        resp = self.client.get(url)
        self.assertEqual(404, resp.status_code)

