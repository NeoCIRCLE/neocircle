from models import ElementTemplate, Machine, Service, ServiceNode, Element, ElementConnection
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.db.models.loading import get_model
from django.db import transaction
from saltstackhelper import SaltStackHelper
from vm.models import Instance
import logging

logger = logging.getLogger(__name__)
salthelper = SaltStackHelper()
class SettyController:
    salthelper = SaltStackHelper()

    '''
    Save the service data given by the designer. It includes all 
    Machines, ServiceNodes and connections between them. If the
    saving fails, the last saved status will not be lost.
    '''
    @staticmethod
    @transaction.atomic
    def saveService(serviceId, serviceName, serviceNodes, machines, elementConnections):
        service = None
        try:
            service = Service.objects.get(id=serviceId)
        except Service.DoesNotExist:
            return {'status': 'error', 'errors': 'SERVICE_NOT_FOUND'}

        service.name = serviceName
        service.save()

        Machine.objects.filter(service=service).delete()
        for machineData in machines:
            machineSaved = Machine(service=service)
            machineSaved.fromDataDictionary(machineData)
            machineSaved.save()

        ServiceNode.objects.filter(service=service).delete()

        for node in serviceNodes:
            elementTemplateId = node["displayId"].split("_")[1]
            elementTemplate = ElementTemplate.objects.get(id=elementTemplateId)
            newNode = get_model('setty', elementTemplate.prototype).clone()

            newNode.service = service
            newNode.fromDataDictionary(node)
            newNode.save()

        for elementConnection in elementConnections:
            sourceId = elementConnection['sourceId']
            targetId = elementConnection['targetId']
            sourceEndpoint = elementConnection['sourceEndpoint']
            targetEndpoint = elementConnection['targetEndpoint']

            targetObject = Element.objects.get(
                display_id=targetId)

            sourceObject = Element.objects.get(
                display_id=sourceId)

            connectionObject = ElementConnection(
                target=targetObject,
                source=sourceObject,
                target_endpoint=targetEndpoint,
                source_endpoint=sourceEndpoint
            )

            connectionObject.save()

        return {'status': 'success', 'serviceName': serviceName}

    '''
    Load all ServiceNode derivatives, ElementConnections and saved Machines
    for the Service with the given id and give it back to the caller.
    If the service doesn't exists, error is returned.
    '''

    @staticmethod
    def loadService(serviceId):
        service = None
        try:
            service = Service.objects.get(id=serviceId)
        except Service.DoesNotExist:
            return {'status': 'error', 'errors': 'SERVICE_NOT_FOUND'}

        machineList = Machine.objects.filter(service=service)
        serviceNodes = []
        elementConnections = []
        machines = []

        for machine in machineList:
            machines.append(machine.getDataDictionary())

        serviveNodeList = ServiceNode.objects.filter(service=service)
        elementConnectionList = ElementConnection.objects.filter(
            Q(target__in=serviveNodeList) | Q(source__in=serviveNodeList))

        for servideNode in serviveNodeList:
            serviceNodes.append(servideNode.cast().getDataDictionary())

        for elementConnection in elementConnectionList:
            elementConnections.append(elementConnection.getDataDictionary())

        return {'serviceName': service.name,
                'elementConnections': elementConnections,
                'serviceNodes': serviceNodes,
                'machines': machines}

    '''
    Queiry information -- field names, type of that field -- about 
    an ElemenTemplate or Machine. If the ElementTemplate doesn't exist
    or the prototype couldn't be retrieved 
    '''

    @staticmethod
    def getInformation(elementTemplateId, hostname):
        if elementTemplateId:
            try:
                elementTemplate = ElementTemplate.objects.get(
                    id=elementTemplateId)
                model = get_model('setty', elementTemplate.prototype)
                return model.getInformation()
            except ElementTemplate.DoesNotExist:
                return {'status': 'error', 'errors': 'ELEMENTTEMPLATE_DOESNT_EXISTS'}
            except LookupError:
                return {'status': 'error', 'errors': 'ELEMENTTEMPLATE_COULDNT_GET_PROTOTYPE'}
        elif hostname:
            return Machine.getInformation()
        elif hostname and elementTemplateId:
            return {'status': 'error', 'errors': 'BOTH_ELEMENTEMPLATE_HOSTNAME_FILLED'}
        else:
            return {'status': 'error', 'errors': 'UNKNOWN_ERROR'}

    ''' 
    Return the available hostnames to add to the Service 
    based on already used / saved hostanames and Instances 
    owned by current user which is also known by SaltStack
    '''

    @staticmethod
    def getMachineAvailableList(serviceId, usedHostnames, current_user):
        savedMachines = Machine.objects.filter(service=serviceId)

        savedHostNames = []
        for machine in savedMachines:
            savedHostNames.append(machine.hostname)

        userInstances = Instance.objects.filter(
            owner=current_user, destroyed_at=None)
        userMachines = []
        for instance in userInstances:
            if instance.vm_name:
                userMachines.append(instance.vm_name)

        usedHostnamesByUser = set(savedHostNames + usedHostnames)
        availableInstances = set(set(userMachines) - usedHostnamesByUser)

        saltMinions = SettyController.salthelper.getAllMinionsUngrouped()
        if not usedHostnamesByUser:
            return {'machinedata': [machineName for machineName in userMachines if machineName in saltMinions]}

        return {'machinedata': [machineName for machineName in availableInstances if machineName in saltMinions]}

    '''
    Add a machine with the given hostname to the Service. If there is a 
    saved Machine with the given hostname or the SaltStack doesn't know about
    the machine give an error back. If it exists and not already saved give 
    back the new Machine instance 
    '''

     #TODO: addMachine requires usedHostnames too for safety
    @staticmethod
    def addMachine(hostname):
        try:
            Machine.objects.get(hostname=hostname)
        except:
            return {'status': 'error', 'errors': 'MACHINE_ALREADY_ADDED'}
        if SettyController.salthelper.checkMinionExists(hostname):
            machine = Machine.clone()
            machine.hostname = hostname
            return machine.getDataDictionary()
        else:
            return {'status': 'error', 'errors': 'MACHINE_DOESNT_EXISTS'}

    '''
    Add a new service node based on the given ElementTemplate ID to 
    the current service and return the data member of it.
    If no ElementTemplate exists with the given ID or it couldn't be
    institiated give an error.
    '''

    @staticmethod
    def addServiceNode(elementTemplateId):
        if elementTemplateId:
            try:
                elementTemplate = ElementTemplate.objects.get(
                    id=elementTemplateId)
                model = get_model('setty', elementTemplate.prototype)
                return model.clone().getDataDictionary()
            except ElementTemplate.DoesNotExist:
                return {'status': 'error', 'errors': 'ELEMENTTEMPLATE_DOESNT_EXISTS'}
            except:
                return {'status': 'error', 'errors': 'ELEMENTTEMPLATE_COULDNT_GET_PROTOTYPE'}
        else:
            return {'status': 'error', 'errors': 'INVALID_ELEMENTTEMPLATE_ID'}

    ''' Deploy a service using SaltStack. The steps are described inline.'''
    @staticmethod
    def deploy(serviceId):
        service = Service.objects.get(id=serviceId)
        serviveNodeList = ServiceNode.objects.filter(service=service)
        errorMessages = []

        nodesToBeDeployed = []
        for serviceNode in serviveNodeList:
            castedServiceNode = serviceNode.cast()
            nodesToBeDeployed.append(castedServiceNode)
            errorMessage = castedServiceNode.checkDependenciesAndAttributes()
            if errorMessage:
                errorMessages.append(errorMessage)

        if errorMessages:
            return {'status': 'error',
                    'errors': errorMessages}

        # phase one: ask the servicenodes to generate their needed salt
        # commands

        for serviceNode in nodesToBeDeployed:
            serviceNode.generateSaltCommands()

        # phase two: sort the nodes by deployment priority(lower the prio,
        # later in the deployement)

        nodesToBeDeployed.sort(reverse=True)

        dbgCheck = []
#        for node in nodesToBeDeployed:
#            commandArray = []
#
#            for command in node.generatedCommands:
#                logger.error( "salt '"+ command.hostname +"' state.sls " + command.command + " pillar=\"" + str(command.parameters) + '"'  )
#                commandArray.append( command.toDict() )
#
#            dbgCheck.append({ "nodeName": str(node.__class__.__name__),
#                "hostingMachineName": str(node.getHostingMachine().hostname ),
#                "commands": commandArray })

        #return {"status": "error", "errors":dbgCheck}

        # phase three: deploy the nodes
        for node in nodesToBeDeployed:
            deployErrorMessages = SettyController.salthelper.executeCommand(
                node.generatedCommands)
            if errorMessages:
                errorMessages.append(deployErrorMessages)

        # phase four: cleanup generated commands 
        for serviceNode in nodesToBeDeployed:
            serviceNode.generatedCommands = None

        if errorMessages:
            return {'status': 'error',
                    'errors': errorMessages}

        return {'status': 'success'}
