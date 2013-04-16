from django.test import TestCase
from models import create_user_profile, Person, Course, Semester
from datetime import datetime, timedelta

class MockUser:
    username = "testuser"

class CreateUserProfileTestCase(TestCase):
    def setUp(self):
        self.user = MockUser()
        for p in Person.objects.all():
            p.delete()

    def test_new_profile(self):
        """Test profile creation functionality for new user."""
        create_user_profile(self.user.__class__, self.user, True)
        self.assertEqual(Person.objects.filter(
            code=self.user.username).count(), 1)

    def test_existing_profile(self):
        """Test profile creation functionality when it already exists."""
        Person.objects.create(code=self.user.username)
        create_user_profile(self.user.__class__, self.user, True)
        self.assertEqual(Person.objects.filter(
            code=self.user.username).count(), 1)


class PersonTestCase(TestCase):
    def setUp(self):
        self.testperson = Person.objects.create(code='testperson')

    def test_language_code_in_choices(self):
        """Test whether the default value for language is a valid choice."""
        # TODO
        language_field = self.testperson._meta.get_field('language')
        choice_codes = [code for (code, _) in language_field.choices]
        self.assertIn(language_field.default, choice_codes)

    def test_get_owned_shares(self):
        # TODO
        self.testperson.get_owned_shares()

    def test_get_shares(self):
        # TODO
        self.testperson.get_shares()

    def test_short_name(self):
        # TODO
        self.testperson.short_name()

    def test_unicode(self):
        # TODO
        self.testperson.__unicode__()

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
