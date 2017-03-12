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


""" Implementation of the OCCI - Infrastructure extension classes """


from occi_core import Resource, Link
from occi_utils import action_list_for_resource, OcciActionInvocationError
from occi_instances import (COMPUTE_ACTIONS, LEASETIME_ACTIONS,
                            STORAGE_ACTIONS, NETWORK_ACTIONS)
from common.models import HumanReadableException
from celery.exceptions import TimeoutError
import logging


logger = logging.getLogger(__name__)


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
            "http://schemas.ogf.org/occi/infrastructure#compute",
            str(vm.pk),
            title=vm.name)
        self.vm = vm
        self.attributes = self.set_attributes()
        self.links = self.set_links()
        self.actions = action_list_for_resource(
            COMPUTE_ACTIONS + LEASETIME_ACTIONS)
        self.mixins = [
            "http://circlecloud.org/occi/infrastructure/compute#credentials",
            "http://circlecloud.org/occi/infrastructure/compute#leasetime",
        ]
        if vm.template:
            self.mixins.append(
                "http://circlecloud.org/occi/templates/os#os_template_" +
                str(vm.template.pk))

    def set_attributes(self):
        """ Sets the attributes of the Compute object based on the VM
            instance. """
        attributes = {}
        attributes["occi.compute.architecture"] = (
            COMPUTE_ARCHITECTURES.get(self.vm.arch))
        attributes["occi.compute.cores"] = self.vm.num_cores
        attributes["occi.compute.hostname"] = self.vm.short_hostname
        attributes["occi.compute.share"] = self.vm.priority
        attributes["occi.compute.memory"] = self.vm.ram_size / 1024.0
        attributes["occi.compute.state"] = COMPUTE_STATES.get(self.vm.state)
        attributes["occi.compute.state.message"] = (
            COMPUTE_STATE_MESSAGES.get(self.vm.state))
        attributes["org.circlecloud.occi.credentials.protocol"] = (
            self.vm.access_method)
        attributes["org.circlecloud.occi.credentials.host"] = (
            self.vm.get_connect_host())
        attributes["org.circlecloud.occi.credentials.port"] = (
            self.vm.get_connect_port())
        attributes["org.circlecloud.occi.credentials.username"] = "cloud"
        attributes["org.circlecloud.occi.credentials.password"] = (
            self.vm.pw)
        attributes["org.circlecloud.occi.credentials.command"] = (
            self.vm.get_connect_command())
        attributes["org.circlecloud.occi.leasetime.suspend"] = (
            unicode(self.vm.time_of_suspend)[:-16])
        attributes["org.circlecloud.occi.leasetime.remove"] = (
            unicode(self.vm.time_of_delete)[:-16])
        return attributes

    def set_links(self):
        links = []
        disks = self.vm.disks.all()
        storages = []
        for disk in disks:
            storages.append(Storage(disk))
        for storage in storages:
            links.append(StorageLink(self, storage).render_as_json())
        nics = [NetworkInterface(self, Network(nic.vlan))
                for nic in self.vm.interface_set.all()]
        for networkinterface in nics:
            links.append(networkinterface.render_as_json())
        return links

    def invoke_action(self, user, action, attributes):
        if action.endswith("start"):
            self.start(user)
        elif action.endswith("stop"):
            self.stop(user, attributes)
        elif action.endswith("restart"):
            self.restart(user, attributes)
        elif action.endswith("suspend"):
            self.suspend(user, attributes)
        elif action.endswith("save"):
            self.save(user, attributes)
        elif action.endswith("renew"):
            self.renew(user)
        else:
            raise OcciActionInvocationError(message="Undefined action.")
        self.__init__(self.vm)

    def renew(self, user):
        try:
            self.vm.renew(user=user, force=True)
        except HumanReadableException as e:
            raise OcciActionInvocationError(message=e.get_user_text())

    def start(self, user):
        """ Start action on a compute instance """
        try:
            if self.vm.status == "SUSPENDED":
                self.vm.wake_up(user=user)
            else:
                self.vm.deploy(user=user)
        except HumanReadableException as e:
            raise OcciActionInvocationError(message=e.get_user_text())

    def stop(self, user, attributes):
        """ Stop action on a compute instance """
        if "method" not in attributes:
            raise OcciActionInvocationError(message="No method given.")
        if attributes["method"] in ("graceful", "acpioff",):
            # NOTE: at kene nezni hogy minden except ag kell-e
            timeout = self.vm.shutdown.remote_timeout + 10
            result = None
            try:
                task = self.vm.shutdown.async(user=user)
            except HumanReadableException as e:
                logger.exception("Could not start operation")
                result = e
            except Exception as e:
                logger.exception("Could not start operation")
                result = e
            else:
                try:
                    task.get(timeout=timeout)
                except TimeoutError:
                    logger.debug("Result didn't arrive in %ss",
                                 timeout, exc_info=True)
                except HumanReadableException as e:
                    logger.exception(e)
                    result = e
                except Exception as e:
                    logger.debug("Operation failed.", exc_info=True)
                    result = e
            if result:
                raise OcciActionInvocationError(unicode(result))
        elif attributes["method"] in ("poweroff",):
            try:
                self.vm.shut_off(user=user)
            except HumanReadableException as e:
                raise OcciActionInvocationError(message=e.get_user_text())
        else:
            raise OcciActionInvocationError(
                message="Given method is not valid")

    def restart(self, user, attributes):
        """ Restart action on a compute instance """
        if "method" not in attributes:
            raise OcciActionInvocationError(message="No method given.")
        if attributes["method"] in ("graceful", "warm",):
            try:
                self.vm.restart(user=user)
            except HumanReadableException as e:
                raise OcciActionInvocationError(message=e.get_user_text())
        elif attributes["method"] in ("cold",):
            try:
                self.vm.reset(user=user)
            except HumanReadableException as e:
                raise OcciActionInvocationError(message=e.get_user_text())
        else:
            raise OcciActionInvocationError(
                message="Given method is not valid")

    def suspend(self, user, attributes):
        """ Suspend action on a compute instance """
        if "method" not in attributes:
            raise OcciActionInvocationError(message="No method given.")
        if attributes["method"] in ("hibernate", "suspend",):
            try:
                self.vm.sleep(user=user)
            except HumanReadableException as e:
                raise OcciActionInvocationError(message=e.get_user_text())
        else:
            raise OcciActionInvocationError(
                message="Given method is not valid")

    def save(self, user, attributes):
        """ Save action on a compute instance """
        # TODO: save template
        raise OcciActionInvocationError(
            message="Save action not implemented")


STORAGE_STATES_BY_IN_USE = {
    "online": "The disk is attached to an active compute instance.",
    "offline": "The disk is not used by any compute instances at the moment.",
    "error": "The disk is destroyed.",
}


class Storage(Resource):
    """ OCCI 1.2 - Infrastructure extension - Storage """

    def __init__(self, disk):
        super(Storage, self).__init__(
            "http://schemas.ogf.org/occi/infrastructure#storage",
            str(disk.pk))
        self.disk = disk
        self.actions = action_list_for_resource(STORAGE_ACTIONS)
        self.attributes = self.set_attributes()

    def set_attributes(self):
        attributes = {}
        attributes["occi.storage.size"] = float(self.disk.size) / 10**9
        if self.disk.destroyed is None:
            if self.disk.is_in_use:
                state_key = "online"
            else:
                state_key = "offline"
        else:
            state_key = "error"

        attributes["occi.storage.state"] = state_key
        attributes["occi.storage.state.message"] = (
            STORAGE_STATES_BY_IN_USE[state_key])
        return attributes

    def invoke_action(self, user, action, attributes):
        message = ("Action invokation on storage instances is not supported. "
                   "Please invoke actions on compute instances instead.")
        raise OcciActionInvocationError(message=message, status=405)


STORAGELINK_STATES_BY_STORAGE_STATE = {
    "online": "active",
    "offline": "inactive",
    "error": "error",
}


class StorageLink(Link):
    """ OCCI 1.2 - Infrastructure extension - StorageLink """

    def __init__(self, compute, storage):
        super(StorageLink, self).__init__(
            {
                "location": "/compute/" + compute.id,
                "kind": "http://schemas.ogf.org/occi/infrastructure#compute",
            },
            {
                "location": "/storage/" + storage.id,
                "kind": "http://schemas.ogf.org/occi/infrastructure#storage",
            },
            "http://schemas.ogf.org/occi/infrastructure#storagelink",
            "compute" + compute.id + "-" + "storage" + storage.id
        )
        self.compute = compute
        self.storage = storage
        self.attributes = self.set_attributes()

    def set_attributes(self):
        attributes = {}
        attributes["occi.storagelink.deviceid"] = self.storage.disk.pk
        attributes["occi.storagelink.mountpoint"] = (
            "/dev/%s%s" % (self.storage.disk.device_type,
                           self.storage.disk.dev_num)
        )
        attributes["occi.storagelink.state"] = (
            STORAGELINK_STATES_BY_STORAGE_STATE[
                self.storage.attributes["occi.storage.state"]])
        attributes["occi.storagelink.state.message"] = (
            self.storage.attributes["occi.storage.state.message"])
        return attributes


class Network(Resource):
    """ OCCI 1.2 - Infrastructure extension - Network """

    def __init__(self, vlan):
        super(Network, self).__init__(
            "http://schemas.ogf.org/occi/infrastructure#network",
            str(vlan.pk),
        )
        self.vlan = vlan
        self.actions = action_list_for_resource(NETWORK_ACTIONS)
        self.attributes = self.set_attributes()
        self.mixins = [
            "http://schemas.ogf.org/occi/infrastructure/network#ipnetwork",
        ]

    def set_attributes(self):
        attributes = {}
        attributes["occi.network.vlan"] = self.vlan.vid
        attributes["occi.network.state"] = "active"
        attributes["occi.network.state.message"] = (
            "The network instance is active.")
        attributes["occi.network.address"] = unicode(self.vlan.network4)
        attributes["occi.network.gateway"] = unicode(self.vlan.network4.ip)
        attributes["occi.network.allocation"] = (
            "static" if self.vlan.dhcp_pool == "" else "dynamic")
        return attributes

    def invoke_action(self, user, action, attributes):
        message = ("Action invokation on network instances is not supported. "
                   "Please invoke actions on compute instances instead.")
        raise OcciActionInvocationError(message=message, status=405)


class NetworkInterface(Link):
    """ OCCI 1.2 - Infrastructure extension - NetworkInterace """

    def __init__(self, compute, network):
        super(NetworkInterface, self).__init__(
            {
                "location": "/compute/" + compute.id,
                "kind": "http://schemas.ogf.org/occi/infrastructure#compute",
            },
            {
                "location": "/network/" + network.id,
                "kind": "http://schemas.ogf.org/occi/infrastructure#network",
            },
            "http://schemas.ogf.org/occi/infrastructure#networkinterface",
            "compute" + compute.id + "-" + "network" + network.id
        )
        self.compute = compute
        self.network = network
        self.interface = compute.vm.interface_set.get(vlan=network.vlan)
        self.mixins = [
            ("http://schemas.ogf.org/occi/infrastructure/networkinterface#" +
             "ipnetworkinterface"),
        ]
        self.attributes = self.set_attributes()

    def set_attributes(self):
        attributes = {}
        attributes["occi.networkinterface.interface"] = (
            self.interface.vlan.name)
        attributes["occi.networkinterface.mac"] = unicode(self.interface.mac)
        attributes["occi.networkinterface.state"] = "active"
        attributes["occi.networkinterface.state.message"] = (
            "The networkinterface is active.")
        attributes["occi.networkinterface.address"] = (
            unicode(self.interface.host.ipv4))
        attributes["occi.networkinterface.gateway"] = (
            unicode(self.interface.vlan.network4.ip))
        attributes["occi.networkinterface.allocation"] = (
            self.network.attributes["occi.network.allocation"])
        return attributes
