from django.test import TestCase
from django.contrib.auth.models import User, Group, AnonymousUser

from ..models import ObjectLevel
from .models import TestModel, Test2Model


class AclUserTest(TestCase):
    def setUp(self):
        self.u1 = User.objects.create(username='user1')
        self.u2 = User.objects.create(username='user2', is_staff=True)
        self.us = User.objects.create(username='superuser', is_superuser=True)
        self.g1 = Group.objects.create(name='group1')
        self.g1.user_set.add(self.u1)
        self.g1.user_set.add(self.u2)
        self.g1.save()
        self.g2 = Group.objects.create(name='group2')
        self.g2.save()

    def test_level_exists(self):
        for codename, name in TestModel.ACL_LEVELS:
            level = TestModel.get_level_object(codename)
            self.assertEqual(level.codename, codename)
        for codename, name in Test2Model.ACL_LEVELS:
            level = Test2Model.get_level_object(codename)
            self.assertEqual(level.codename, codename)

    def test_lowest_user_level(self):
        i = TestModel.objects.create(normal_field='Hello')
        self.assertFalse(i.has_level(self.u1, 'alfa', False))
        self.assertFalse(i.has_level(self.u1, 'bravo', False))
        i.set_level(self.u1, 'alfa')
        i.set_level(self.g1, 'bravo')
        self.assertTrue(i.has_level(self.u1, 'alfa', False))
        self.assertFalse(i.has_level(self.u1, 'bravo', False))

    def test_anonymous_user_level(self):
        i = TestModel.objects.create(normal_field='Hello')
        anon = AnonymousUser()
        self.assertFalse(i.has_level(anon, 'alfa'))
        self.assertFalse(i.has_level(anon, 'bravo'))

    def test_middle_user_level(self):
        i = TestModel.objects.create(normal_field='Hello')
        self.assertFalse(i.has_level(self.u1, 'alfa'))
        self.assertFalse(i.has_level(self.u1, 'bravo'))
        self.assertFalse(i.has_level(self.u1, 'charlie'))
        i.set_level(self.u1, 'bravo')
        self.assertTrue(i.has_level(self.u1, 'alfa'))
        self.assertTrue(i.has_level(self.u1, 'bravo'))
        self.assertFalse(i.has_level(self.u1, 'charlie'))

    def test_level_set_twice_same(self):
        i = TestModel.objects.create(normal_field='Hello')
        self.assertFalse(i.has_level(self.u1, 'alfa'))
        self.assertFalse(i.has_level(self.u1, 'bravo'))
        self.assertFalse(i.has_level(self.u1, 'charlie'))
        i.set_level(self.u1, 'bravo')
        i.set_level(self.u1, 'bravo')
        self.assertTrue(i.has_level(self.u1, 'alfa'))
        self.assertTrue(i.has_level(self.u1, 'bravo'))
        self.assertFalse(i.has_level(self.u1, 'charlie'))

    def test_level_set_twice_different(self):
        i = TestModel.objects.create(normal_field='Hello')
        self.assertFalse(i.has_level(self.u1, 'alfa'))
        self.assertFalse(i.has_level(self.u1, 'bravo'))
        self.assertFalse(i.has_level(self.u1, 'charlie'))
        i.set_level(self.u1, 'charlie')
        i.set_level(self.u1, 'bravo')
        self.assertTrue(i.has_level(self.u1, 'alfa'))
        self.assertTrue(i.has_level(self.u1, 'bravo'))
        self.assertFalse(i.has_level(self.u1, 'charlie'))

    def test_superuser(self):
        i = TestModel.objects.create(normal_field='Hello')
        for u, v in [(self.u1, False), (self.u2, False), (self.us, True)]:
            self.assertEqual(i.has_level(u, 'alfa'), v)
            self.assertEqual(i.has_level(u, 'bravo'), v)
            self.assertEqual(i.has_level(u, 'charlie'), v)

    def test_check_group_membership(self):
        groups = self.u1.groups.values_list('id', flat=True)
        self.assertIn(self.g1.id, groups)

        self.assertTrue(self.g1.user_set.filter(id=self.u2.id).exists())

    def test_lowest_group_level(self):
        i = TestModel.objects.create(normal_field='Hello')
        self.assertFalse(i.has_level(self.u1, 'alfa'))
        self.assertFalse(i.has_level(self.u1, 'bravo'))
        i.set_level(self.g1, 'alfa')
        self.assertTrue(i.has_level(self.u1, 'alfa'))
        self.assertFalse(i.has_level(self.u1, 'bravo'))

    def test_middle_group_level(self):
        i = TestModel.objects.create(normal_field='Hello')
        self.assertFalse(i.has_level(self.u1, 'alfa'))
        self.assertFalse(i.has_level(self.u1, 'bravo'))
        self.assertFalse(i.has_level(self.u1, 'charlie'))
        i.set_level(self.g1, 'bravo')
        self.assertTrue(i.has_level(self.u1, 'alfa'))
        self.assertTrue(i.has_level(self.u1, 'bravo'))
        self.assertFalse(i.has_level(self.u1, 'charlie'))

    def test_set_level_error_handling(self):
        with self.assertRaises(AttributeError):
            TestModel.objects.create().set_level('wrong arg', 'level')

    def test_get_users_with_level(self):
        i1 = TestModel.objects.create(normal_field='Hello')
        i2 = Test2Model.objects.create(normal2_field='Hello2')
        i1.set_level(self.u1, 'bravo')
        i1.set_level(self.u2, 'charlie')
        i2.set_level(self.u1, 'one')
        i2.set_level(self.us, u'three')
        res1 = i1.get_users_with_level()
        self.assertEqual([(self.u1, u'bravo'), (self.u2, u'charlie')], res1)
        res2 = i2.get_users_with_level()
        self.assertEqual([(self.u1, u'one'), (self.us, u'three')], res2)

    def test_get_groups_with_level(self):
        i1 = TestModel.objects.create(normal_field='Hello')
        i2 = Test2Model.objects.create(normal2_field='Hello2')
        i1.set_level(self.g1, 'bravo')
        i1.set_level(self.u2, 'charlie')
        i2.set_level(self.g1, 'one')
        i2.set_level(self.us, u'three')
        res1 = i1.get_groups_with_level()
        self.assertEqual([(self.g1, u'bravo')], res1)
        res2 = i2.get_groups_with_level()
        self.assertEqual([(self.g1, u'one')], res2)

    def test_object_level_unicode(self):
        i1 = TestModel.objects.create(normal_field='Hello')
        i1.set_level(self.g1, 'bravo')
        unicode(ObjectLevel.objects.all()[0])

    def test_set_user_level_none(self):
        i = TestModel.objects.create(normal_field='Hello')
        i.set_level(self.u1, 'alfa')
        self.assertTrue(i.has_level(self.u1, 'alfa'))
        i.set_level(self.u1, None)
        self.assertFalse(i.has_level(self.u1, 'alfa'))

    def test_set_group_level_none(self):
        i = TestModel.objects.create(normal_field='Hello')
        i.set_level(self.g1, 'alfa')
        self.assertTrue(i.has_level(self.u1, 'alfa'))
        i.set_level(self.g1, None)
        self.assertFalse(i.has_level(self.u1, 'alfa'))

    def test_get_objects_with_level(self):
        i1 = TestModel.objects.create(normal_field='Hello1')
        i2 = TestModel.objects.create(normal_field='Hello2')
        i1.set_level(self.u1, 'alfa')
        i2.set_level(self.u1, 'bravo')
        i2.set_level(self.u2, 'bravo')
        self.assertItemsEqual(
            TestModel.get_objects_with_level('alfa', self.u1), [i1, i2])
        self.assertItemsEqual(
            TestModel.get_objects_with_level('alfa', self.u2), [i2])

    def test_get_objects_with_level_for_group(self):
        i1 = TestModel.objects.create(normal_field='Hello1')
        i2 = TestModel.objects.create(normal_field='Hello2')
        i1.set_level(self.g1, 'alfa')
        i2.set_level(self.g1, 'bravo')
        i2.set_level(self.u1, 'bravo')
        self.assertItemsEqual(
            TestModel.get_objects_with_level('alfa', self.u1), [i1, i2])

    def test_get_objects_with_group_level(self):
        i1 = TestModel.objects.create(normal_field='Hello1')
        i2 = TestModel.objects.create(normal_field='Hello2')
        i1.set_level(self.g1, 'alfa')
        i2.set_level(self.g1, 'bravo')
        i2.set_level(self.g2, 'bravo')
        self.assertItemsEqual(
            TestModel.get_objects_with_group_level('alfa', self.g1), [i1, i2])
        self.assertItemsEqual(
            TestModel.get_objects_with_group_level('alfa', self.g2), [i2])

    def test_owner(self):
        i = Test2Model.objects.create(normal2_field='Hello',
                                      owner=self.u1)
        self.assertTrue(i.has_level(self.u1, 'one'))
        self.assertTrue(i.has_level(self.u1, 'owner'))
        self.assertFalse(i.has_level(self.u2, 'owner'))

    def test_owner_change(self):
        i = Test2Model.objects.create(normal2_field='Hello',
                                      owner=self.u1)
        self.assertTrue(i.has_level(self.u1, 'one'))
        self.assertTrue(i.has_level(self.u1, 'owner'))
        self.assertFalse(i.has_level(self.u2, 'owner'))
        i.owner = self.u2
        i.save()
        self.assertTrue(i.has_level(self.u1, 'one'))
        self.assertTrue(i.has_level(self.u1, 'owner'))
        self.assertTrue(i.has_level(self.u2, 'owner'))

    def test_owner_change_from_none(self):
        i = Test2Model.objects.create(normal2_field='Hello')
        self.assertFalse(i.has_level(self.u1, 'one'))
        self.assertFalse(i.has_level(self.u1, 'owner'))
        self.assertFalse(i.has_level(self.u2, 'owner'))
        i.owner = self.u2
        i.save()
        self.assertFalse(i.has_level(self.u1, 'one'))
        self.assertFalse(i.has_level(self.u1, 'owner'))
        self.assertTrue(i.has_level(self.u2, 'owner'))
