from .models import *
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.db.models.loading import get_model
from saltstackhelper import *
import os

class SettyController:
	salthelper = SaltStackHelper()

	@staticmethod
	def saveService( serviceId, serviceName, serviceNodes, machines, elementConnections ):
		service = None
		try:
		    service = Service.objects.get(id=serviceId)
		except Service.DoesNotExist:
		    return JsonResponse( {'error': 'Service not found'})

		service.name = serviceName
		service.save()

		#first check machine names
		#validMachineNames = self.salthelper.getAllMinionsUngrouped()
		Machine.objects.filter(service=service).delete()
		for machineData in machines:
		 #   if machineData["hostname"] in validMachineNames:
		    machineSaved = Machine(service=service)
		    machineSaved.fromDataDictionary( machineData )
		    machineSaved.save()

		ServiceNode.objects.filter(service=service).delete()
		for node in serviceNodes:
		    elementTemplateId = node["displayId"].split("_")[0]
		    elementTemplate = ElementTemplate.objects.get(id=elementTemplateId)
		    newNode = get_model('setty', elementTemplate.prototype ).clone()

		    newNode.service = service
		    newNode.fromDataDictionary( node )
		    newNode.save()

		for elementConnection in elementConnections:
		    sourceId = elementConnection['sourceId']
		    targetId = elementConnection['targetId']
		    sourceEndpoint = elementConnection['sourceEndpoint']
		    targetEndpoint = elementConnection['targetEndpoint']
		    connectionParameters = elementConnection['parameters']

		    targetObject = Element.objects.get(
		        display_id=targetId)

		    sourceObject = Element.objects.get(
		        display_id=sourceId)

		    connectionObject = ElementConnection(
		        target=targetObject,
		        source=sourceObject,
		        target_endpoint=targetEndpoint,
		        source_endpoint=sourceEndpoint,
		        parameters=connectionParameters
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
	        serviceNodes.append( servideNode.cast().getDataDictionary() )

	    for elementConnection in elementConnectionList:
	        elementConnections.append( elementConnection.getDataDictionary() )

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
	def getMachineAvailableList(service_id, used_hostnames):
	    all_minions = SettyController.salthelper.getAllMinionsGrouped()
	    result = []
	    #TODO: filter out used ones
	    for item in all_minions["up"]:
	        result.append( {'hostname': item,
	                        'hardware-info': SettyController.salthelper.getMinionBasicHardwareInfo( item ),
	                        'status': 'up'} )

	    for item in all_minions["down"]:
	        result.append( {'hostname': item, 'status': 'down' })

	    return { 'machinedata': result }

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
	            elementTemplate = ElementTemplate.objects.get(id=elementTemplateId)
	            model = get_model('setty', elementTemplate.prototype )
	            return model.clone().getDataDictionary()
	        except ElementTemplate.DoesNotExist:
	            return {'error': 'lofaszka' }
	        except:
	            return {'error': 'valami nagyon el lett baszva'}
	    else:
	        return {'error': 'templateid'}

	@staticmethod
	def deploy(serviceId):
		service  = Service.objects.get(id=serviceId)
		machines = Machine.objects.filter(service=service)
		elementConnections = ElementConnection.objects.filter(
	        Q(target__in=machines) | Q(source__in=machines) )

		firstLevelServiceNodes = []
		#phase one: set the machine ptr in serviceNodes which can be accessed by
		# connections from machines
		for machine in machines:
			for connection in elementConnections:
				serviceNode = None
				if connection.target.cast() == machine:
					serviceNode = connection.source.cast()
					serviceNode.setMachineForDeploy( machine )

				elif connection.source.cast() == machine:
					serviceNode = connection.target.cast()
					serviceNode.setMachineForDeploy( machine )
				else:
					raise PermissionDenied
				firstLevelServiceNodes.append( serviceNode )

		#phase two: let the nodes create configurations recursively
		configuratedNodes = list()
		for serviceNode in firstLevelServiceNodes:
			generatedNodes = serviceNode.generateConfigurationRecursively()
			if isinstance( generatedNodes, list ):
				configuratedNodes = configuratedNodes + generatedNodes
			else:
				configuratedNodes.append( generatedNodes )

		#phase three: sort the nodes by deployment priority(lower the prio, later in the deployement)
		
		configuratedNodes.sort(reverse=True)

		#deploy the nodes
		for node in configuratedNodes:
			SettyController.salthelper.deploy( node.machine.hostname, node.generatedConfig )
		return {'status': 'deployed'}

		#cleanup the temporary data
'''		for node in configuratedNodes:
			node.deployCleanUp()'''