""" Required instances of the OCCI classes """

from occi_core import Kind, Mixin, Attribute, Action


ENTITY_KIND = Kind("http://schemas.ogf.org/occi/core#", "entity",
                   title="Entity")

RESOURCE_KIND = Kind("http://schemas.ogf.org/occi/core#", "resource",
                     title="Resource",
                     parent="http://schemas.ogf.org/occi/core#entity")

LINK_KIND = Kind("http://schemas.ogf.org/occi/core#", "link",
                 title="Link",
                 parent="http://schemas.ogf.org/occi/ocre#entity")

COMPUTE_ATTRIBUTES = [
    Attribute("occi.compute.architecture", "Enum {x86, x64}", True, False,
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
           attributes=[Attribute("method", "Enum {hot, deferred}",
                                 True, False),
                       Attribute("name", "String", True, True), ]),
]

COMPUTE_KIND = Kind("http://schemas.ogf.org/occi/infrastructure#", "compute",
                    title="Compute", location="/compute/",
                    parent="http://schemas.ogf.org/occi/core#resource",
                    actions=COMPUTE_ACTIONS, attributes=COMPUTE_ATTRIBUTES)

NETWORK_ATTRIBUTES = [
    Attribute("occi.network.vlan", "Integer: 0-4095", True, False,
              description="802.1q VLAN Identifier (e.g., 343)."),
    Attribute("occi.network.label", "Token", True, False,
              description="Tag based VLANs (e.g., external-dmz)."),
    Attribute("occi.network.state", "Enum {active, inactive, error}", False,
              True, description="Current state of the instance."),
    Attribute("occi.network.state.message", "String", False, False,
              description="Human-readable explanation of the current " +
              "instance state."),
]

NETWORK_ACTIONS = [
    Action("http://schemas.ogf.org/occi/infrastructure/network/action#",
           "up", title="Activate the network interface."),
    Action("http://schemas.ogf.org/occi/infrastructure/network/action#",
           "down", title="Deactivate the network interface."),
]

NETWORK_KIND = Kind("http://schemas.ogf.org/occi/infrastructure#", "network",
                    title="Network Interface", location="/network/",
                    parent="http://schemas.ogf.org/occi/core#resource",
                    actions=NETWORK_ACTIONS, attributes=NETWORK_ATTRIBUTES)

IPNETWORK_ATTRIBUTES = [
    Attribute("occi.network.address", "IPv4 or IPv6 Address range, CIDR " +
              "notation", True, False, description="Internet Protocol (IP) " +
              "network address (e.g., 192.168.0.1/24, fc00::/7)"),
    Attribute("occi.network.gateway", "IPv4 or IPv6 address", True, False,
              description="Internet Protocol (IP) network address (e.g., " +
              "192.168.0.1, fc00::)"),
    Attribute("occi.network.allocation", "Enum {dynamic, static}", True, False,
              description="Address allocation mechanism: dynamic e.g., uses " +
              "the dynamic host configuration protocol, static e.g., uses " +
              "user supplied static network configurations."),
]

IPNETWORK_MIXIN = Mixin("http://schemas.ogf.org/occi/infrastructure/network#",
                        "ipnetwork", title="IP Network Mixin",
                        location="/network/ipnetwork",
                        applies=("http://shemas.ogf.org/occi/infrastructure" +
                                 "#network"))

STORAGE_ATTRIBUTES = [
    Attribute("occi.storage.size", "Float, 10^9 (GiB)", True, True,
              description="Storage size of the instance in gigabytes."),
    Attribute("occi.storage.state", "Enum {online, offline, error}", False,
              True, description="Current status of the instance."),
    Attribute("occi.storage.state.message", "String", False, False,
              description="Human-readable explanation of the current " +
              "instance state"),
]

STORAGE_ACTIONS = [
    Action("http://schemas.ogf.org/occi/infrastructure/storage/action#",
           "online", title="Activate the storage instance"),
    Action("http://schemas.ogf.org/occi/infrastructure/storage/action#",
           "offline", title="Deactivate the storage instance"),
]

STORAGE_KIND = Kind("http://schemas.ogf.org/occi/infrastructure#", "storage",
                    title="Storage", location="/storage/",
                    parent="http://schemas.ogf.org/occi/core#resource",
                    actions=STORAGE_ACTIONS, attributes=STORAGE_ATTRIBUTES)

NETWORKINTERFACE_ATTRIBUTES = [
    Attribute("occi.networkinterface.interface", "String", False, True,
              description="Identifier that relates the link to the link's " +
              "decive interface."),
    Attribute("occi.networkinterface.mac", "String", True, True,
              description="MAC address associated with the link's device " +
              "interface"),
    Attribute("occi.networkinterface.state", "Enum {active, inactive, error}",
              False, True, description="Current status of the interface."),
    Attribute("occi.networkinterface.state.message", "String", False, False,
              description="Human-readable explanation of the current " +
              "instance state."),
]

NETWORKINTERFACE_KIND = Kind("http://schemas.ogf.org/occi/infrastructure#",
                             "networkinterface", title="Network Interface",
                             location="/networkinterface/",
                             parent="http://schemas.ogf.org/occi/core#link",
                             attributes=NETWORKINTERFACE_ATTRIBUTES)

IPNETWORKINTERFACE_ATTRIBUTES = [
    Attribute("occi.networkinterface.address", "IPv4 or IPv6 Address", True,
              True, description="Internet Protocol (IP) network address " +
              "(e.g., 192.168.0.1/24, fc00::/7) of the link."),
    Attribute("occi.networkinterface.gateway", "IPv4 or IPv6 Address", True,
              False, description="Internet Protocol (IP) network address " +
              "(e.g., 192.168.0.1/24, fc00::/7)"),
    Attribute("occi.networkinterface.allocation", "Enum {dynamic, static}",
              True, True, description="Address mechanism: dynamic e.g., uses" +
              " the dynamic host configuration protocol, static e.g., uses " +
              "user supplied network configurations."),
]

IPNETWORKINTERFACE_MIXIN = Mixin("http://schemas.ogf.org/occi/" +
                                 "infrastructure/networkinterface#",
                                 "ipnetworkinterface",
                                 title="IP Network Interface Mixin",
                                 location="/networkinterface" +
                                          "/ipnetworkinterface/",
                                 applies="http://schemas.ogf.org/occi/" +
                                 "infrastructure#networkinterface")

STORAGELINK_ATTRIBUTES = [
    Attribute("occi.storagelink.deviceid", "String", True, True,
              description="Device identifier as defined by the OCCI service " +
              "provider."),
    Attribute("occi.storagelink.mountpoint", "String", True, False,
              description="Point to where the storage is mounted in the " +
              "guest OS."),
    Attribute("occi.storagelink.state", "Enum {active, inactive, error}",
              False, True, description="Current status of the instance."),
    Attribute("occi.storagelink.state.message", "String", False, False,
              description="Human-readable explanation of the current " +
              "instance state."),
]

STORAGELINK_KIND = Kind("http://schemas.ogf.org/occi/infrastructure#",
                        "storagelink", title="Storage Link",
                        location="/storagelink/",
                        parent="http://schemas.ogf.org/occi/core#link",
                        atrributes=STORAGELINK_ATTRIBUTES)

# TODO: OS Templates and Credentials

ACTION_ARRAYS = [COMPUTE_ACTIONS, NETWORK_ACTIONS, STORAGE_ACTIONS]


def ALL_KINDS():
    return [ENTITY_KIND, RESOURCE_KIND, LINK_KIND, COMPUTE_KIND, NETWORK_KIND,
            STORAGE_KIND, NETWORKINTERFACE_KIND]


def ALL_MIXINS():
    return [IPNETWORK_MIXIN, IPNETWORKINTERFACE_MIXIN]


def ALL_ACTIONS():
    result = []
    for actions in ACTION_ARRAYS:
        for action in actions:
            result.append(action)
    return result
