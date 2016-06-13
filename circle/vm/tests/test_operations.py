# Copyright 2014 Budapest University of Technology and Economics (BME IK)
#
# This file is part of CIRCLE Cloud.
#
# CIRCLE is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# CIRCLE is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along
# with CIRCLE.  If not, see <http://www.gnu.org/licenses/>.

from django.test import TestCase
from mock import MagicMock

from common.operations import operation_registry_name as op_reg_name
from vm.models import Instance, InstanceActivity, Node
from vm.operations import (
    DeployOperation, DestroyOperation, FlushOperation, MigrateOperation,
    RebootOperation, ResetOperation, SaveAsTemplateOperation,
    ShutdownOperation, ShutOffOperation, SleepOperation, WakeUpOperation,
)
from test_models import DiskQuerySet


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

    def test_operation_wo_to_node_param(self):
        class MigrateException(Exception):
            pass

        inst = MagicMock(spec=Instance)
        act = MagicMock(spec=InstanceActivity)
        op = MigrateOperation(inst)
        op._get_remote_args = MagicMock(side_effect=MigrateException())
        inst.select_node = MagicMock(return_value='test')
        inst.disks = DiskQuerySet()
        self.assertRaises(
            MigrateException, op._operation,
            act, user=None, to_node=None)
        assert inst.select_node.called
        op._get_remote_args.assert_called_once_with(
            to_node='test', live_migration=True)


class RebootOperationTestCase(TestCase):
    def test_operation_registered(self):
        assert RebootOperation.id in getattr(Instance, op_reg_name)


class ResetOperationTestCase(TestCase):
    def test_operation_registered(self):
        assert ResetOperation.id in getattr(Instance, op_reg_name)


class SaveAsTemplateOperationTestCase(TestCase):
    def test_operation_registered(self):
        assert SaveAsTemplateOperation.id in getattr(Instance, op_reg_name)

    def test_rename(self):
        self.assertEqual(SaveAsTemplateOperation._rename("foo"), "foo v1")
        self.assertEqual(SaveAsTemplateOperation._rename("foo v2"), "foo v3")
        self.assertEqual(SaveAsTemplateOperation._rename("foo v"), "foo v v1")
        self.assertEqual(SaveAsTemplateOperation._rename("foo v9"), "foo v10")
        self.assertEqual(
            SaveAsTemplateOperation._rename("foo v111"), "foo v112")


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
