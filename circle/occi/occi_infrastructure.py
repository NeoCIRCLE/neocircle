""" Implementation of the OCCI - Infrastructure extension classes """


from occi_core import Resource
from occi_utils import action_list_for_resource, OcciActionInvocationError
from occi_instances import COMPUTE_ACTIONS
from common.models import HumanReadableException


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
            str(vm.pk))
        self.vm = vm
        self.attributes = self.set_attributes()
        self.actions = action_list_for_resource(COMPUTE_ACTIONS)
        self.mixins = [
            "http://circlecloud.org/occi/infrastructure#credentials",
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
        return attributes

    def invoke_action(self, user, action, attributes):
        base = "http://schemas.ogf.org/occi/infrastructure/compute/action#"
        if action == (base + "start"):
            self.start(user)
        elif action == (base + "stop"):
            self.stop(user, attributes)
        elif action == (base + "restart"):
            self.restart(user, attributes)
        elif action == (base + "suspend"):
            self.suspend(user, attributes)
        elif action == (base + "save"):
            self.save(user, attributes)
        else:
            raise OcciActionInvocationError(message="Undefined action.")
        self.__init__(self.vm)

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
            try:
                # TODO: call shutdown properly
                self.vm.shutdown(user=user)
            except HumanReadableException as e:
                raise OcciActionInvocationError(message=e.get_user_text())
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
                # TODO: not working for some reason
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
