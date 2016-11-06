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

import salt.loader
import salt.config
import salt.runner
import salt.client

import logging

logger = logging.getLogger(__name__)

class SaltCommand:

    def __init__(self):
        self.hostname = ""
        self.command = ""
        self.parameters = None

    # For debugging purposes only
    def toDict(self):
        return {'hostname': self.hostname,
                'command': self.command,
                'parameters': self.parameters}


class SaltStackHelper:

    def __init__(self):
        self.master_opts = salt.config.client_config('/etc/salt/master')
        self.salt_runner = salt.runner.RunnerClient(self.master_opts)
        self.salt_localclient = salt.client.LocalClient()

    def getAllMinionsGrouped(self):
        query_result = self.salt_runner.cmd('manage.status', [])
        return query_result

    def getAllMinionsUngrouped(self):
        query_result = self.salt_runner.cmd('manage.status', [])
        return query_result["up"] + query_result["down"]

    def getRunningMinions(self):
        return self.salt_runner.cmd('manage.up', [])

    def getUnavailableMinions(self):
        return self.salt_runner.cmd('manage.down', [])

    def checkMinionExists(self, hostname):
        query_res = self.salt_localclient.cmd(hostname, 'network.get_hostname')
        return query_res != {}

    def getIpAddressOfMinion(self, hostname):
        query_res = self.salt_localclient.cmd(hostname, 'network.ip_addrs')
        return query_res[hostname][0]

    def executeCommand(self, saltCommands):
        for command in saltCommands:
            if command.parameters:
                self.salt_localclient.cmd(command.hostname, "state.sls",
                                      [command.command],
                                      kwarg={"pillar": command.parameters})
            else:
                self.salt_localclient.cmd(command.hostname, "state.sls",
                                      [command.command])
