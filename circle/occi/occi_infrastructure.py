""" Implementation of the OCCI - Infrastructure extension classes """


from occi_core import Action, Attribute, Resource
from occi_utils import action_list_for_resource


COMPUTE_ATTRIBUTES = [
    Attribute("occi.compute.architecture", "Object", True, False,
              description="CPU Architecture of the instance."),
    Attribute("occi.compute.cores", "Object", True, False,
              description="Number of virtual CPU cores assigned to " +
              "the instance."),
    Attribute("occi.compute.hostname", "Object", True, False,
              description="Fully Qualified DNS hostname for the " +
              "instance"),
    Attribute("occi.compute.share", "Object", True, False,
              description="Relative number of CPU shares for the " +
              "instance."),
    Attribute("occi.compute.memory", "Object", True, False,
              description="Maximum RAM in gigabytes allocated to " +
              "the instance."),
    Attribute("occi.compute.state", "Object", False, True,
              description="Current state of the instance."),
    Attribute("occi.compute.state.message", "Object", False, False,
              description="Human-readable explanation of the current " +
              "instance state"),
]

COMPUTE_ACTIONS = [
    Action("http://schemas.ogf.org/occi/infrastructure/compute/action#",
           "start", title="Start compute instance"),
    Action("http://schemas.ogf.org/occi/infrastructure/compute/action#",
           "stop", title="Stop compute instance",
           attributes=[Attribute("method", "Object", True, False), ]),
    Action("http://schemas.ogf.org/occi/infrastructure/compute/action#",
           "restart", title="Restart compute instance",
           attributes=[Attribute("method", "Object",
                                 True, False), ]),
    Action("http://schemas.ogf.org/occi/infrastructure/compute/action#",
           "suspend", title="Suspend compute instance",
           attributes=[Attribute("method", "Object",
                                 True, False), ]),
    Action("http://schemas.ogf.org/occi/infrastructure/compute/action#",
           "save", title="Create a template of compute instance",
           attributes=[Attribute("method", "Object", True,
                                 False),
                       Attribute("name", "Object", True, True), ]),
]

COMPUTE_STATES = {
    "NOSTATE": "inactive",
    "RUNNING": "active",
    "STOPPED": "inactive",
    "SUSPENDED": "suspended",
    "ERROR": "error",
    "PENDING": "inactive",
    "DESTROYED": "inactive",
}

COMPUTE_STATE_MESSAGES = {
    "NOSTATE": "The virtual machine is not in a valid state.",
    "RUNNING": "The virtual machine is running.",
    "STOPPED": "The virtual machine is stopped.",
    "SUSPENDED": "The virtual machine is suspended.",
    "ERROR": "The virtual machine is in error state.",
    "PENDING": "There is an action going on.",
    "DESTROYED": "The virtual machine is destroyed",
}

COMPUTE_ARCHITECTURES = {"x86_64": "x64",
                         "x86-64 (64 bit)": "x64",
                         "i686": "x86",
                         "x86 (32 bit)": "x86"}


class Compute(Resource):
    """ OCCI 1.2 - Infrastructure extension - Compute """
    def __init__(self, vm):
        """ Creates a Compute instance of a VM instance object """
        super(Compute, self).__init__(
            "http://schemas.ogf.org/occi/infrastructure#compute", vm.pk)
        self.vm = vm
        self.attributes = self.set_attributes()

        self.actions = action_list_for_resource(COMPUTE_ACTIONS)

    def set_attributes(self):
        """ Sets the attributes of the Compute object based on the VM
            instance. """
        attributes = {}
        attributes["occi.compute.architecture"] = (COMPUTE_ARCHITECTURES
                                                   .get(self.vm.arch))
        attributes["occi.compute.cores"] = self.vm.num_cores
        attributes["occi.compute.hostname"] = self.vm.short_hostname
        attributes["occi.compute.share"] = self.vm.priority
        attributes["occi.compute.memory"] = self.vm.ram_size / 1024.0
        attributes["occi.compute.state"] = COMPUTE_STATES.get(self.vm.state)
        attributes["occi.compute.state.message"] = (COMPUTE_STATE_MESSAGES
                                                    .get(self.vm.state))
        return attributes
