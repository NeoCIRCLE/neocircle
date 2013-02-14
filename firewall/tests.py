from django.test import TestCase
from admin import HostAdmin

class MockInstance:
    def __init__(self, groups):
        self.groups = MockGroups(groups)

class MockGroup:
    def __init__(self, name):
        self.name = name

class MockGroups:
    def __init__(self, groups):
        self.groups = groups

    def all(self):
        return self.groups

class HostAdminNoGroupTestCase(TestCase):
    def runTest(self):
        instance = MockInstance([])
        l = HostAdmin.groups_l(instance)
        self.assertEqual(l, "")

class HostAdminSingleGroupTestCase(TestCase):
    def runTest(self):
        instance = MockInstance([MockGroup("alma")])
        l = HostAdmin.groups_l(instance)
        self.assertEqual(l, "alma")

class HostAdminMultipleGroupsTestCase(TestCase):
    def runTest(self):
        instance = MockInstance([MockGroup("alma"),
            MockGroup("korte"), MockGroup("szilva")])
        l = HostAdmin.groups_l(instance)
        self.assertEqual(l, "alma, korte, szilva")
