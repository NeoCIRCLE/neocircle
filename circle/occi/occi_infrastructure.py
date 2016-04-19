""" Implementation of the OCCI - Infrastructure extension classes """


from occi_core import Action, Attribute, Resource


COMPUTE_ATTRIBUTES = [
    Attribute("occi.compute.architecture", "Enum {x86, x84}", True, False,
              description="CPU Architecture of the instance."),
    Attribute("occi.compute.cores", "Integer", True, False,
              description="Number of virtual CPU cores assigned to " +
              "the instance."),
    Attribute("occi.compute.hostname", "String", True, False,
              description="Fully Qualified DNS hostname for the " +
              "instance"),
    Attribute("occi.compute.share", "Integer", True, False,
              description="Relative number of CPU shares for the " +
              "instance."),
    Attribute("occi.compute.memory", "Float, 10^9 (GiB)", True, False,
              description="Maximum RAM in gigabytes allocated to " +
              "the instance."),
    Attribute("occi.compute.state", "Enum {active, inactive, suspended, " +
              "error}", False, True,
              description="Current state of the instance."),
    Attribute("occi.compute.state.message", "String", False, False,
              description="Human-readable explanation of the current " +
              "instance state"),
]

COMPUTE_ACTIONS = [
    Action("http://schemas.ogf.org/occi/infrastructure/compute/action#",
           "start", title="Start compute instance"),
    Action("http://schemas.ogf.org/occi/infrastructure/compute/action#",
           "stop", title="Stop compute instance",
           attributes=[Attribute("method", "Enum {graceful, acpioff, " +
                                 "poweroff}", True, False), ]),
    Action("http://schemas.ogf.org/occi/infrastructure/compute/action#",
           "restart", title="Restart compute instance",
           attributes=[Attribute("method", "Enum {graceful, warm, cold}",
                                 True, False), ]),
    Action("http://schemas.ogf.org/occi/infrastructure/compute/action#",
           "suspend", title="Suspend compute instance",
           attributes=[Attribute("method", "Enum {hibernate, suspend}",
                                 True, False), ]),
    Action("http://schemas.ogf.org/occi/infrastructure/compute/action#",
           "save", title="Create a template of compute instance",
           attributes=[Attribute("method", "Enum {hot, deffered}", True,
                                 False),
                       Attribute("name", "String", True, True), ]),
]


class Compute(Resource):
    """ OCCI 1.2 - Infrastructure extension - Compute """
    def __init__(self, vm):
        """ Creates a Compute instance of a VM instance object """
        self.location = "/compute/%d" % (vm.pk)
        self.vm = vm
