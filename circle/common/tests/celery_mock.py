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

from mock import patch


class MockCeleryMixin(object):
    def _pre_setup(self):
        self.reloadtask_patcher = patch(
            'firewall.tasks.local_tasks.reloadtask.apply_async', spec=True)
        self.reloadtask_patcher.start()

        self.kombu_patcher = patch('kombu.connection.Connection.ensure',
                                   side_effect=RuntimeError())
        self.kombu_patcher.start()

        self.check_queue_patcher = patch('vm.tasks.vm_tasks.check_queue',
                                         return_value=True)
        self.check_queue_patcher.start()

        super(MockCeleryMixin, self)._pre_setup()

    def _post_teardown(self):
        self.reloadtask_patcher.stop()
        self.kombu_patcher.stop()

        super(MockCeleryMixin, self)._post_teardown()
