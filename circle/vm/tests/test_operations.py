from django.test import TestCase

from vm.models import Instance
from vm.operations import (
    DeployOperation, DestroyOperation, MigrateOperation,
    RebootOperation, RedeployOperation, ResetOperation,
    SaveAsTemplateOperation, ShutdownOperation, ShutOffOperation,
    SleepOperation, WakeUpOperation,
)


class DeployOperationTestCase(TestCase):
    def test_operation_registered(self):
        assert DeployOperation.id in Instance._ops


class DestroyOperationTestCase(TestCase):
    def test_operation_registered(self):
        assert DestroyOperation.id in Instance._ops


class MigrateOperationTestCase(TestCase):
    def test_operation_registered(self):
        assert MigrateOperation.id in Instance._ops


class RebootOperationTestCase(TestCase):
    def test_operation_registered(self):
        assert RebootOperation.id in Instance._ops


class RedeployOperationTestCase(TestCase):
    def test_operation_registered(self):
        assert RedeployOperation.id in Instance._ops


class ResetOperationTestCase(TestCase):
    def test_operation_registered(self):
        assert ResetOperation.id in Instance._ops


class SaveAsTemplateOperationTestCase(TestCase):
    def test_operation_registered(self):
        assert SaveAsTemplateOperation.id in Instance._ops


class ShutdownOperationTestCase(TestCase):
    def test_operation_registered(self):
        assert ShutdownOperation.id in Instance._ops


class ShutOffOperationTestCase(TestCase):
    def test_operation_registered(self):
        assert ShutOffOperation.id in Instance._ops


class SleepOperationTestCase(TestCase):
    def test_operation_registered(self):
        assert SleepOperation.id in Instance._ops


class WakeUpOperationTestCase(TestCase):
    def test_operation_registered(self):
        assert WakeUpOperation.id in Instance._ops
