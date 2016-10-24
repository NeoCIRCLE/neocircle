import salt.loader
import salt.config
import salt.runner
import salt.client

class SaltCommand:
    def __init__(self):
        self.hostname = ""
        self.command = ""
        self.parameters = ""

    # For debugging purposes only
    def __str__(self):
	   return "Command: " + self.hostname + " - " + self.command + " - " + str(self.parameters)

    def toDict(self):
        return { 'hostname': self.hostname, 'command': self.command, 'parameters': self.parameters }


class SaltStackHelper:
    def __init__(self):
        self.master_opts = salt.config.client_config('/etc/salt/master')
        self.salt_runner = salt.runner.RunnerClient(self.master_opts)
        self.salt_localclient = salt.client.LocalClient()

    def getAllMinionsGrouped(self):
        query_result = self.salt_runner.cmd('manage.status', []);
        return query_result

    def getAllMinionsUngrouped(self):
        query_result = self.salt_runner.cmd('manage.status', []);
        return query_result["up"] + query_result["down"]

    def getRunningMinions(self):
        return self.salt_runner.cmd('manage.up', []);

    def getUnavailableMinions(self):
        return self.salt_runner.cmd('manage.down', []);

    def getMinionBasicHardwareInfo(self, hostname):
        query_res = self.salt_localclient.cmd( hostname,'grains.items' );
        if query_res:
            return {
                'CpuModel': query_res[hostname]['cpu_model'],
                'CpuArch': query_res[hostname]['cpuarch'],
                'TotalMemory': query_res[hostname]['mem_total'],
                'OSDescription': query_res[hostname]['lsb_distrib_description'] }

        return query_res

    def checkMinionExists(self, hostname):
        query_res = self.salt_localclient.cmd( hostname,'network.get_hostname' );
        return query_res != {}

    def executeCommand(self, saltCommands):
        for saltCommand in saltCommands:
            self.salt_localclient.cmd(saltCommand.hostname, "state.sls",[saltCommand.command],kwarg={"pillar":saltCommand.parameters} )
