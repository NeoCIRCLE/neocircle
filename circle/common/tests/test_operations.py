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

from mock import MagicMock, patch

from django.test import TestCase

from ..operations import Operation


class OperationTestCase(TestCase):
    def test_activity_created_before_async_job(self):
        class AbortEx(Exception):
            pass

        op = Operation(MagicMock())
        op.activity_code_suffix = 'test'
        op.id = 'test'
        op.async_operation = MagicMock(
            apply_async=MagicMock(side_effect=AbortEx))

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

    def test_auth_check_on_non_system_call(self):
        op = Operation(MagicMock())
        op.activity_code_suffix = 'test'
        op.id = 'test'
        user = MagicMock()
        with patch.object(Operation, 'check_auth') as check_auth:
            with patch.object(Operation, 'check_precond'), \
                    patch.object(Operation, 'create_activity'), \
                    patch.object(Operation, '_exec_op'):
                op.call(user=user)
            check_auth.assert_called_with(user)

    def test_no_auth_check_on_system_call(self):
        op = Operation(MagicMock())
        op.activity_code_suffix = 'test'
        op.id = 'test'
        with patch.object(Operation, 'check_auth', side_effect=AssertionError):
            with patch.object(Operation, 'check_precond'), \
                    patch.object(Operation, 'create_activity'), \
                    patch.object(Operation, '_exec_op'):
                op.call(system=True)
