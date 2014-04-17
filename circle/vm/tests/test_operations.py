from django.test import TestCase

from common.operations import operation_registry_name as op_reg_name
from vm.models import Instance, Node
from vm.operations import (
    DeployOperation, DestroyOperation, FlushOperation, MigrateOperation,
    RebootOperation, ResetOperation, SaveAsTemplateOperation,
    ShutdownOperation, ShutOffOperation, SleepOperation, WakeUpOperation,
)


class DeployOperationTestCase(TestCase):
    def test_operation_registered(self):
        assert DeployOperation.id in getattr(Instance, op_reg_name)


class DestroyOperationTestCase(TestCase):
    def test_operation_registered(self):
        assert DestroyOperation.id in getattr(Instance, op_reg_name)


class FlushOperationTestCase(TestCase):
    def test_operation_registered(self):
        assert FlushOperation.id in getattr(Node, op_reg_name)


class MigrateOperationTestCase(TestCase):
    def test_operation_registered(self):
        assert MigrateOperation.id in getattr(Instance, op_reg_name)


class RebootOperationTestCase(TestCase):
    def test_operation_registered(self):
        assert RebootOperation.id in getattr(Instance, op_reg_name)


class ResetOperationTestCase(TestCase):
    def test_operation_registered(self):
        assert ResetOperation.id in getattr(Instance, op_reg_name)


class SaveAsTemplateOperationTestCase(TestCase):
    def test_operation_registered(self):
        assert SaveAsTemplateOperation.id in getattr(Instance, op_reg_name)


class ShutdownOperationTestCase(TestCase):
    def test_operation_registered(self):
        assert ShutdownOperation.id in getattr(Instance, op_reg_name)


class ShutOffOperationTestCase(TestCase):
    def test_operation_registered(self):
        assert ShutOffOperation.id in getattr(Instance, op_reg_name)


class SleepOperationTestCase(TestCase):
    def test_operation_registered(self):
        assert SleepOperation.id in getattr(Instance, op_reg_name)


class WakeUpOperationTestCase(TestCase):
    def test_operation_registered(self):
        assert WakeUpOperation.id in getattr(Instance, op_reg_name)
