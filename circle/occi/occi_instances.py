# Copyright 2017 Budapest University of Technology and Economics (BME IK)
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


""" Required instances of the OCCI classes """

from vm.models.instance import InstanceTemplate
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


CREDENTIALS_ATTRIBUTES = [
    Attribute("org.circlecloud.occi.credentials.protocol", "String", False,
              False, description="The protocol to be used to access the "
              "compute instance."),
    Attribute("org.circlecloud.occi.credentials.host", "String", False,
              False, description="The host to be used to access the compute " +
              "instance."),
    Attribute("org.circlecloud.occi.credentials.port", "Integer", False,
              False, description="The port to be used to access the compute " +
              "instance."),
    Attribute("org.circlecloud.occi.credentials.username", "String", False,
              False, description="The username to be used to access the " +
              "compute instance."),
    Attribute("org.circlecloud.occi.credentials.password", "String", False,
              False, description="The password to be used to acces the " +
              "compute instance."),
    Attribute("org.circlecloud.occi.credentials.command", "String", False,
              False, description="The full command that may be used to " +
              "connect to the compute instance."),
]

CREDENTIALS_MIXIN = Mixin("http://circlecloud.org/occi/infrastructure/" +
                          "compute#",
                          "credentials",
                          title="Credentials Mixin",
                          attributes=CREDENTIALS_ATTRIBUTES,
                          applies="http://schemas.ogf.org/occi/" +
                          "infrastructure#compute")

LEASETIME_ATTRIBUTES = [
    Attribute("org.circlecloud.occi.leasetime.suspend", "String", False,
              False, description="The time remaining until the compute " +
              "instance is suspended."),
    Attribute("org.circlecloud.occi.leasetime.remove", "String", False,
              False, description="The time remaining until the compute " +
              "instance is deleted."),

]

LEASETIME_ACTIONS = [
    Action("http://circlecloud.org/occi/infrastructure/compute/action#",
           "renew", title="Renew the lease time of the compute instance."),
]

LEASETIME_MIXIN = Mixin("http://circlecloud.org/occi/infrastucture/compute#",
                        "leasetime",
                        title="Compute Lease Time Mixin",
                        attributes=LEASETIME_ATTRIBUTES,
                        actions=LEASETIME_ACTIONS,
                        applies="http://schemas.ogf.org/occi/infrastructure" +
                        "#compute")

OS_TPL_MIXIN = Mixin("http://schemas.ogf.org/occi/infrastructure#",
                     "os_tpl",
                     title="OS Template")

ACTION_ARRAYS = [
    COMPUTE_ACTIONS,
    NETWORK_ACTIONS,
    STORAGE_ACTIONS,
    LEASETIME_ACTIONS,
]


def ALL_KINDS():
    return [
        ENTITY_KIND,
        RESOURCE_KIND,
        LINK_KIND,
        COMPUTE_KIND,
        NETWORK_KIND,
        STORAGE_KIND,
        NETWORKINTERFACE_KIND,
        STORAGELINK_KIND,
    ]


def os_tpl_mixins(user):
    """ Returns an array of all the templates the user has access to. """
    templates = InstanceTemplate.get_objects_with_level("user", user)
    result = []
    for template in templates:
        result.append(Mixin("http://circlecloud.org/occi/templates/os#",
                            "os_template_" + str(template.pk),
                            title=template.name,
                            depends=(OS_TPL_MIXIN.scheme + OS_TPL_MIXIN.term)))
    return result


def ALL_MIXINS(user):
    mixins = [
        IPNETWORK_MIXIN,
        IPNETWORKINTERFACE_MIXIN,
        CREDENTIALS_MIXIN,
        OS_TPL_MIXIN,
        LEASETIME_MIXIN,
    ]
    template_mixins = os_tpl_mixins(user)
    for template in template_mixins:
        mixins.append(template)
    return mixins


def ALL_ACTIONS():
    result = []
    for actions in ACTION_ARRAYS:
        for action in actions:
            result.append(action)
    return result
