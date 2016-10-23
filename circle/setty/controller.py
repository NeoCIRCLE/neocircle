from .models import *
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.db.models.loading import get_model
from django.db import transaction
from saltstackhelper import *
import os
from vm.models import Instance
import logging

class SettyController:
    salthelper = SaltStackHelper()

    @staticmethod
    @transaction.atomic
    def saveService(serviceId, serviceName, serviceNodes, machines, elementConnections):
        service = None
        try:
            service = Service.objects.get(id=serviceId)
        except Service.DoesNotExist:
            return JsonResponse({'error': 'Service not found'})

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

        return {"serviceName": serviceName}

    @staticmethod
    def loadService(serviceId):
        service = None

        try:
            service = Service.objects.get(id=serviceId)
        except Service.DoesNotExist:
            return JsonResponse({'error': 'Service not found'})

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

    @staticmethod
    def getInformation(elementTemplateId, hostname):
        if elementTemplateId:
            try:
                elementTemplate = ElementTemplate.objects.get(
                    id=elementTemplateId)
                model = get_model('setty', elementTemplate.prototype)
                return model.getInformation()
            except ElementTemplate.DoesNotExist:
                return
            except LookupError:
                return
        elif hostname:
            return Machine.getInformation()
        elif hostname and elementTemplateId:
            raise PermissionDenied  # TODO: something more meaningful
        else:
            raise PermissionDenied  # TODO: something more meaningful

    @staticmethod
    def getMachineAvailableList(serviceId, usedHostnames, current_user):
        saltMinions = SettyController.salthelper.getAllMinionsUngrouped()
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

        if not usedHostnamesByUser:
            
            return {'machinedata': [machineName for machineName in userMachines if machineName in saltMinions] }

        availableInstances = list(set(userMachines) - usedHostnamesByUser)
        return {'machinedata': [ machineName for machineName in availableInstances if machineName in saltMinions ]}

    @staticmethod
    def addMachine(hostname):
        try:
            Machine.objects.get(hostname=hostname)
            return {'error': 'already added or doesnt exists'}
        except:
            pass
        if SettyController.salthelper.checkMinionExists(hostname):
            machine = Machine.clone()
            machine.hostname = hostname
            return machine.getDataDictionary()
        else:
            return {'error': 'already added or doesnt exists'}

    @staticmethod
    def addServiceNode(elementTemplateId):
        if elementTemplateId:
            try:
                elementTemplate = ElementTemplate.objects.get(
                    id=elementTemplateId)
                model = get_model('setty', elementTemplate.prototype)
                return model.clone().getDataDictionary()
            except ElementTemplate.DoesNotExist:
                return {'error': "ElementTemplate doesn't exists"}
            except:
                return {'error': 'Can not get prototype'}
        else:
            return {'error': 'templateid'}

    @staticmethod
    def deploy(serviceId):
        service = Service.objects.get(id=serviceId)
        machines = Machine.objects.filter(service=service)

        serviveNodeList = ServiceNode.objects.filter(service=service)
        errorMessages = []
        for serviceNode in serviveNodeList:
            errorMessage = serviceNode.cast().checkDependenciesAndAttributes()
            if errorMessage:
                errorMessages.append(errorMessage)

        if errorMessages:
            return {'status': 'error',
                    'errors': errorMessages}

        elementConnections = ElementConnection.objects.filter(
            Q(target__in=machines) | Q(source__in=machines))

        # phase one: set the machine ptr in serviceNodes which can be accessed by
        # connections from machines
        logger = logging.getLogger('project.interesting.stuff')
        for machine in machines:
            for connection in elementConnections:
                serviceNode = None
                if connection.target.cast() == machine:
                    serviceNode = connection.source.cast()
                    serviceNode.setMachineForDeploy(machine)
                elif connection.source.cast() == machine:
                    serviceNode = connection.target.cast()
                    serviceNode.setMachineForDeploy(machine)

        # phase two: let the nodes create configurations recursively
        configuratedNodes = list()
        for serviceNode in serviveNodeList:
            node = serviceNode.cast()
            node.generateSaltCommands()
            configuratedNodes.append( node )

        # phase three: sort the nodes by deployment priority(lower the prio,
        # later in the deployement)

        configuratedNodes.sort(reverse=True)

#        dbgCheck = []
#        for node in configuratedNodes:
#            commandDict = []
#            for command in node.generatedCommands:
#                commandDict.append( command.__dict__ )
#            dbgCheck.append({ "nodeName": my_instance.__class__.__name__,
#                "commands": commandDict })
#        return dbgCheck
        # phase four: deploy the nodes
        for node in configuratedNodes:
            deployErrorMessages = SettyController.salthelper.executeCommand(
                node.generatedCommands)
            if errorMessages:
                errorMessages.append(deployErrorMessages)

        # phase five: cleanup generated commands
        for serviceNode in firstLevelServiceNodes:
            serviceNode.generatedCommands = None

        if errorMessages:
            return {'status': 'error',
                    'errors': errorMessages}

        return {'status': 'success'}
