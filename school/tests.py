from datetime import datetime, timedelta
from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User, Group as AuthGroup
from django.core.exceptions import ValidationError
from models import create_user_profile, Person, Course, Semester, Group

class CreateUserProfileTestCase(TestCase):
    def setUp(self):
        self.user = User(username="testuser", password="testpass",
                email="test@mail.com", first_name="Test", last_name="User")
        Person.objects.all().delete()
        with self.assertRaises(Person.DoesNotExist):
            Person.objects.get(code=self.user.username)

    def test_new_profile(self):
        """Test profile creation functionality for new user."""
        create_user_profile(self.user.__class__, self.user, True)
        self.assertIsNotNone(Person.objects.get(code=self.user.username))

    def test_existing_profile(self):
        """Test profile creation functionality when it already exists."""
        Person.objects.create(code=self.user.username)
        create_user_profile(self.user.__class__, self.user, True)
        self.assertIsNotNone(Person.objects.get(code=self.user.username))

class PersonTestCase(TestCase):
    """Test 'static' Person facts."""
    def test_language_code_in_choices(self):
        """Test whether the default value for language is a valid choice."""
        person = Person(code="test")
        language_field = person._meta.get_field('language')
        choice_codes = [code for (code, _) in language_field.choices]
        self.assertIn(language_field.default, choice_codes)

class PersonWithUserTestCase(TestCase):
    """Test Person entities which have their user attribute set."""
    def setUp(self):
        self.user = User(username="testuser", password="testpass",
                email="test@mail.com", first_name="Test", last_name="User")
        Person.objects.all().delete()
        self.person = Person.objects.create(code='testcode', user=self.user)

    def test_get_owned_shares(self):
        self.assertIsNotNone(self.person.get_owned_shares())

    def test_get_shares(self):
        self.assertIsNotNone(self.person.get_shares())

    def test_short_name(self):
        self.assertIsNotNone(self.person.short_name())
        # without first or last name
        self.person.user.first_name = None
        self.person.user.last_name = None
        self.assertIsNotNone(self.person.short_name())

    def test_unicode(self):
        self.assertIsNotNone(self.person.__unicode__())
        # without first or last name
        self.person.user.first_name = None
        self.person.user.last_name = None
        self.assertIsNotNone(self.person.__unicode__())

class PersonWithoutUserTestCase(TestCase):
    """Test Person entities which doesn't have their user attribute set."""
    def setUp(self):
        Person.objects.all().delete()
        self.person = Person.objects.create(code='testcode')

    def test_get_owned_shares(self):
        self.assertIsNotNone(self.person.get_owned_shares())

    def test_get_shares(self):
        self.assertIsNotNone(self.person.get_shares())

    def test_short_name(self):
        self.assertIsNotNone(self.person.short_name())

    def test_unicode(self):
        self.assertIsNotNone(self.person.__unicode__())

class CourseTestCase(TestCase):
    def setUp(self):
        now = datetime.now()
        date = now.date()
        delta = timedelta(weeks=7)
        self.testperson1 = Person.objects.create(code="testperson1")
        self.testperson2 = Person.objects.create(code="testperson2")
        self.testsemester = Semester.objects.create(name="testsemester",
                start=date-delta, end=date+delta)
        self.testcourse = Course.objects.create(code="testcode",
                name="testname", short_name="tn")
        self.testcourse.owners.add(self.testperson1, self.testperson2)

    def test_get_or_create_default_group(self):
        default_group = self.testcourse.get_or_create_default_group()
        self.assertIsNotNone(default_group)
        self.assertEqual(default_group, self.testcourse.default_group)
        # now it already has a group, so this'll be a get
        default_group1 = self.testcourse.get_or_create_default_group()
        self.assertIsNotNone(default_group1)
        self.assertEqual(default_group, default_group1)

    def test_owner_list(self):
        self.assertIsNotNone(self.testcourse.owner_list())
        # if the course has no owners:
        self.testcourse.owners.all().delete()
        self.assertIsNotNone(self.testcourse.owner_list())

    def test_unicode(self):
        self.assertIsNotNone(self.testcourse.__unicode__())
        # if the course doesn't have a name:
        self.testcourse.name = None
        self.assertIsNotNone(self.testcourse.__unicode__())

    def test_short(self):
        self.assertIsNotNone(self.testcourse.short())
        # if the course doesn't have a short name:
        self.testcourse.short_name = None
        self.assertIsNotNone(self.testcourse.short())

class SemesterTestCase(TestCase):
    def setUp(self):
        now = datetime.now()
        date = now.date()
        self.now = now
        delta = timedelta(weeks=7)
        self.last_semester = Semester.objects.create(name="testsem1",
                start=date-3*delta, end=date-delta)
        self.current_semester = Semester.objects.create(name="testsem2",
                start=date-delta, end=date+delta)
        self.next_semester = Semester.objects.create(name="testsem3",
                start=date+delta, end=date+3*delta)

    def test_is_on(self):
        self.assertFalse(self.last_semester.is_on(self.now))
        self.assertTrue(self.current_semester.is_on(self.now))
        self.assertFalse(self.next_semester.is_on(self.now))

    def test_get_current(self):
        self.assertEqual(self.current_semester, Semester.get_current())
        # if there's no current semester:
        self.current_semester.delete()
        with self.assertRaises(ValidationError):
            Semester.get_current()

    def test_unicode(self):
        self.current_semester.__unicode__()

class GroupTestCase(TestCase):
    def setUp(self):
        date = datetime.now().date()
        delta = timedelta(weeks=7)
        semester = Semester.objects.create(name="testsem",
                start=date-delta, end=date+delta)
        self.testcourse = Course.objects.create(code="testcode",
                name="testname", short_name="tn")
        self.testgroup = Group.objects.create(name="testgrp",
                semester=semester, course=self.testcourse)

    def test_owner_list(self):
        self.assertIsNotNone(self.testgroup.owner_list())
        testowner1 = Person.objects.create(code="testprsn1")
        self.testgroup.owners.add(testowner1)
        self.assertIsNotNone(self.testgroup.owner_list())
        testowner2 = Person.objects.create(code="testprsn2")
        self.testgroup.owners.add(testowner2)
        self.assertIsNotNone(self.testgroup.owner_list())
        self.assertIn(", ", self.testgroup.owner_list())

    def test_member_count(self):
        self.assertEqual(0, self.testgroup.member_count())
        testmember1 = Person.objects.create(code="testprsn3")
        self.testgroup.members.add(testmember1)
        self.assertEqual(1, self.testgroup.member_count())
        testmember2 = Person.objects.create(code="testprsn4")
        self.testgroup.members.add(testmember2)
        self.assertEqual(2, self.testgroup.member_count())

    def test_unicode(self):
        self.assertIsNotNone(self.testgroup.__unicode__())
        # if the group has no course associated:
        self.testgroup.course = None
        self.assertIsNotNone(self.testgroup.__unicode__())

    def test_get_absolute_url(self):
        self.assertIsNotNone(self.testgroup.get_absolute_url())

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

