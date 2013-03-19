from django.test import TestCase
from models import create_user_profile, Person

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
