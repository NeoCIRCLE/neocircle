from datetime import datetime, timedelta
from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User, Group as AuthGroup
from django.core.exceptions import ValidationError
from ..models import create_user_profile, Person, Course, Semester, Group

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

    def test_logout(self):
        resp = self.client.get('/logout/', follow=False)
        self.assertEqual(302, resp.status_code)

    def test_login(self):
        resp = self.client.get('/login/', follow=True, **self.http_headers)
        self.assertEqual(200, resp.status_code)

    def test_login_without_id(self):
        del self.http_headers['niifPersonOrgID']
        resp = self.client.get('/login/', follow=True, **self.http_headers)
        self.assertEqual(200, resp.status_code)
        (url, _) = resp.redirect_chain[0]
        self.assertIn('/admin', url)

    def test_login_without_email(self):
        del self.http_headers['email']
        resp = self.client.get('/login/', follow=True, **self.http_headers)
        self.assertEqual(403, resp.status_code)

    def test_login_without_affiliation(self):
        del self.http_headers['affiliation']
        resp = self.client.get('/login/', follow=True, **self.http_headers)
        self.assertEqual(200, resp.status_code)

    def test_login_without_group_for_affiliation(self):
        self.group1.delete()
        resp = self.client.get('/login/', follow=True, **self.http_headers)
        self.assertEqual(200, resp.status_code)

    def test_language(self):
        self.client.get('/login/', **self.http_headers)
        u = User.objects.get(username=self.http_headers['niifPersonOrgID'])
        p = Person.objects.get(user=u)
        lang = u'en' if p.language == u'hu' else u'hu'
        self.http_headers['HTTP_REFERER'] = '/'
        resp = self.client.get('/language/%s/' % lang, follow=False,
                **self.http_headers)
        self.assertEqual(302, resp.status_code)
        p = Person.objects.get(user=u)
        self.assertEqual(lang, p.language)

    def test_language_with_invalid_parameter(self):
        self.client.get('/login/', **self.http_headers)
        u = User.objects.get(username=self.http_headers['niifPersonOrgID'])
        lang = u'nemvanez' # invalid language
        self.http_headers['HTTP_REFERER'] = '/'
        resp = self.client.get('/language/%s/' % lang, follow=False,
                **self.http_headers)
        self.assertEqual(302, resp.status_code)
        p = Person.objects.get(user=u)
        self.assertEqual(lang, p.language)

    def test_language_without_person_for_user(self):
        self.client.get('/login/', **self.http_headers)
        u = User.objects.get(username=self.http_headers['niifPersonOrgID'])
        Person.objects.get(user=u).delete()
        lang = u'en'
        self.http_headers['HTTP_REFERER'] = '/'
        resp = self.client.get('/language/%s/' % lang, follow=False,
                **self.http_headers)
        self.assertEqual(302, resp.status_code)

    def test_group_show(self):
        self.client.get('/login/', **self.http_headers)
        resp = self.client.get('/group/show/%s/' % self.group1.id)
        self.assertEqual(200, resp.status_code)

    def test_group_show_with_nonexistent_groupid(self):
        self.client.get('/login/', **self.http_headers)
        gid = 1337 # this should be the ID of a non-existent group,
        # so if it exists, delete it!
        Group.objects.filter(id=gid).delete()
        resp = self.client.get('/group/show/%s/' % gid)
        self.assertEqual(404, resp.status_code)

