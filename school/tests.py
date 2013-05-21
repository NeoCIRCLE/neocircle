from datetime import datetime, timedelta
from django.test import TestCase
from django.contrib.auth.models import User
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
        self.assertEquals(default_group, self.testcourse.default_group)

    def test_owner_list(self):
        owner_list = self.testcourse.owner_list()
        self.assertIsNotNone(owner_list)

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

    def test_unicode(self):
        self.current_semester.__unicode__()

class GroupTestCase(TestCase):
    def setUp(self):
        date = datetime.now().date()
        delta = timedelta(weeks=7)
        semester = Semester.objects.create(name="testsem",
                start=date-delta, end=date+delta)
        self.testgroup = Group.objects.create(name="testgrp",
                semester=semester)

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
