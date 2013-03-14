from django.test import TestCase
from models import create_user_profile, Person

class MockUser:
    username = "testuser"

class CreateUserProfileTestCase(TestCase):
    def setUp(self):
        for p in Person.objects.all():
            p.delete()

    def test_new_profile(self):
        """Test profile creation functionality for new user."""
        user = MockUser()
        create_user_profile(user.__class__, user, True)
        self.assertEqual(Person.objects.filter(code=user.username).count(), 1)

    def test_existing_profile(self):
        """Test profile creation functionality when it already exists."""
        user = MockUser()
        Person.objects.create(code=user.username)
        create_user_profile(user.__class__, user, True)
        self.assertEqual(Person.objects.filter(code=user.username).count(), 1)


class PersonTestCase(TestCase):
    def setUp(self):
        Person.objects.create()

    def test_language_code_in_choices(self):
        """Test whether the default value for language is a valid choice."""
        language_field = Person.objects.all()[0]._meta.get_field('language')
        choice_codes = [code for (code, _) in language_field.choices]
        self.assertIn(language_field.default, choice_codes)
