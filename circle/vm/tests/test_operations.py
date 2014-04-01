from mock import MagicMock, patch

from django.test import TestCase

from vm.models import Instance
from vm.operations import (
    Operation, DeployOperation, DestroyOperation, MigrateOperation,
    RebootOperation, RedeployOperation, ResetOperation,
    SaveAsTemplateOperation, ShutdownOperation, ShutOffOperation,
    SleepOperation, WakeUpOperation,
)
from vm.tasks.local_tasks import async_operation


class OperationTestCase(TestCase):
    def test_activity_created_before_async_job(self):
        class AbortEx(Exception):
            pass

        op = Operation(MagicMock())
        op.activity_code_suffix = 'test'
        op.id = 'test'
        with patch.object(async_operation, 'apply_async', side_effect=AbortEx):
            with patch.object(Operation, 'check_precond'):
                with patch.object(Operation, 'create_activity') as create_act:
                    try:
                        op.async(system=True)
                    except AbortEx:
                        self.assertTrue(create_act.called)

    def test_check_precond_called_before_create_activity(self):
        class AbortEx(Exception):
            pass

        op = Operation(MagicMock())
        op.activity_code_suffix = 'test'
        op.id = 'test'
        with patch.object(Operation, 'create_activity', side_effect=AbortEx):
            with patch.object(Operation, 'check_precond') as chk_pre:
                try:
                    op.call(system=True)
                except AbortEx:
                    self.assertTrue(chk_pre.called)


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
