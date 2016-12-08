# Copyright 2014 Budapest University of Technology and Economics (BME IK)
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

from django.db import models
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.utils.translation import ugettext
from storage import OverwriteStorage
import os
import yaml
from saltstackhelper import SaltCommand, SaltStackHelper

SALTSTACK_PILLAR_FOLDER = "/srv/pillar"

# Replacer method for configuration generation

salthelper = SaltStackHelper()


def replaceParameter(pillar, parameterToReplace, newValue):
    pillarEdited = pillar.replace(parameterToReplace, str(newValue))
    return pillarEdited


def createErrorMessage(errorMessage, nodeType, nodeName):
    message = nodeType
    if(nodeName):
        message = message + "(" + nodeName + ")"
    message = message + ": " + errorMessage
    return message


class Service(models.Model):
    SERVICE_STATUS_CHOICES = ((1, 'Draft'),
                              (2, 'Deployed'))

    user = models.ForeignKey(User)
    name = models.TextField(verbose_name="Name")
    status = models.CharField(
        choices=SERVICE_STATUS_CHOICES, max_length=1, default=1)

    def __unicode__(self):
        return self.name

''' Defines caterogies for ElementTemplates. '''


class ElementCategory(models.Model):
    name = models.CharField(max_length=50)  # Name of the category
    # If the current category is a subcategory, store the ancestor
    parent_category = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True)

    def __unicode__(self):
        return self.name

'''
Defines a model for ElementTemplates which are used to create real elements ServiceNodes
'''


class ElementTemplate(models.Model):
    name = models.CharField(max_length=50)
    logo = models.FileField(
        upload_to='setty/', storage=OverwriteStorage())  # Logo for the
    description = models.TextField()  # Description of a ServiceNode
    # List of wich ServiceNodes are compatible
    compatibles = models.ManyToManyField('self', blank=True)
    category = models.ForeignKey(
        ElementCategory, on_delete=models.CASCADE, null=True)  # Which category
    # The name of the Model which the template represents
    prototype = models.TextField(default="<SYNTAX ERROR>")

    def __unicode__(self):
        return self.name

'''
http://stackoverflow.com/questions/929029/how-do-i-access-the-child-classes-of-an-object-in-django-without-knowing-the-name/929982#929982
Base class to prevent messing with the code in the controller
it saves the type info to DB, and when the objects are queried, the cast method returns the real class
not the base
'''


class InheritanceCastModel(models.Model):
    real_type = models.ForeignKey(ContentType, editable=False, default=None)

    def save(self, *args, **kwargs):
        if not self.id:
            self.real_type = self._get_real_type()
        super(InheritanceCastModel, self).save(*args, **kwargs)

    def _get_real_type(self):
        return ContentType.objects.get_for_model(type(self))

    def cast(self):
        return self.real_type.get_object_for_this_type(pk=self.pk)

    class Meta:
        abstract = True

'''
Element stores the base information for all types of nodes shown in the designer.
It stores the id, position and number of anchors
'''


class Element(InheritanceCastModel):
    display_id = models.TextField()
    position_left = models.FloatField()
    position_top = models.FloatField()
    anchor_number = models.PositiveSmallIntegerField()

    # Get the display related data in a dictionary
    def getDisplayData(self):
        return {'displayId': self.display_id,
                'positionLeft': self.position_left,
                'positionTop': self.position_top,
                'anchorNumber': self.anchor_number}

    # Set the display related data from a dictionary
    def setDisplayData(self, data):
        self.display_id = data["displayId"]
        self.position_left = data["positionLeft"]
        self.position_top = data["positionTop"]
        self.anchor_number = data["anchorNumber"]

''' 
ElementConnection represents connection between Elements. Has a source
and a target endpoint.
'''


class ElementConnection(models.Model):
    target = models.ForeignKey(
        Element,
        related_name='target',
        on_delete=models.CASCADE)
    source = models.ForeignKey(
        Element,
        related_name='source',
        on_delete=models.CASCADE)
    source_endpoint = models.TextField()
    target_endpoint = models.TextField()

    def __unicode__(self):
        return "%d" % self.id

    def getDataDictionary(self):
        return {'targetEndpoint': self.target_endpoint,
                'sourceEndpoint': self.source_endpoint}

'''
Represents an CIRCLE VM Instance which is known by Salt-Master and used
in Setty configuration
'''


class Machine(Element):
    MACHINE_STATUS_CHOICES = (
        (1, 'Running'),
        (2, 'Unreachable'))

    # Which service contains the given Machine instnace
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="service_id")
    hostname = models.TextField(null=False)  # also serves as salt-minion id
    # User given alias  for the machine
    alias = models.CharField(max_length=50)
    # User's description for the machine
    description = models.TextField(default="")
    status = models.CharField(choices=MACHINE_STATUS_CHOICES, max_length=1)

    def __unicode__(self):
        return "%s" % self.hostname

    # Get the name and the type of the editable fields
    @staticmethod
    def getInformation():
        return {'hostname': Machine._meta.get_field('hostname').get_internal_type(),
                'alias': Machine._meta.get_field('alias').get_internal_type(),
                'description': Machine._meta.get_field('description').get_internal_type()}

    # Get the all the Machine related data in a dictionary
    def getDataDictionary(self):
        element_data = self.getDisplayData()

        self_data = {'hostname': self.hostname,
                     'alias': self.alias,
                     'description': self.description}

        element_data.update(self_data)
        return element_data
    # Fill the fields from the given dictioary

    def fromDataDictionary(self, data):
        self.setDisplayData(data)
        self.hostname = data["hostname"]
        self.alias = data["alias"]
        self.description = data["description"]

    # Create a new instance of Machine
    @staticmethod
    def clone():
        return Machine()


class ServiceNode(Element):
    # The Service which the ServiceNode belongs to
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, default=None)
    name = models.CharField(max_length=50)
    # User's description for the ServiceNode
    description = models.TextField(default="")

    # Override the default init function to create generatedCommands
    # instance member to store the SaltCommands for deployment
    def __init__(self, *args, **kwargs):
        super(ServiceNode, self).__init__(*args, **kwargs)
        self.generatedCommands = []

    def __unicode__(self):
        return "%s" % self.name

    # Get the saved data from the node
    def getDataDictionary(self):
        element_data = self.getDisplayData()

        self_data = {'name': self.name,
                     'description': self.description}

        element_data.update(self_data)
        return element_data

    # Fill the members of the class from dictionary
    def fromDataDictionary(self, data):
        self.setDisplayData(data)
        self.name = data['name']
        self.description = data['description']

    # Get fieldnames and types in a dictionary
    @staticmethod
    def getInformation():
        return {'name': ServiceNode._meta.get_field('name').get_internal_type(),
                'description': ServiceNode._meta.get_field('description').get_internal_type()}

    @staticmethod
    def clone():
        raise PermissionDenied

    # functions for deployement
    # Check that all the required fields are set, and
    # has the connections for the other services or machines
    # which are needed
    def checkDependenciesAndAttributes(self):
        return []

    # Checks whether the current Node has a connection to
    # an other node (Machine or ServiceNode derivative).
    # The other object's type is the ObjOther parameter
    # Returns the queryed node if it exists, or None
    def checkDependecy(self, ObjOther):
        elementConnections = ElementConnection.objects.filter(
            Q(target=self) | Q(source=self))

        for connection in elementConnections:
            if connection.target.cast() == self:
                if isinstance(connection.source.cast(), ObjOther):
                    return connection.source.cast()
            elif connection.source.cast() == self:
                if isinstance(connection.target.cast(), ObjOther):
                    return connection.target.cast()
        return None

    # Compare functions for sorting the ServiceNodes by DeploymentPriority
    def __cmp__(self, other):
        if not isinstance(other, ServiceNode):
            raise PermissionDenied

        return self.getDeploymentPriority(self).__cmp__(other.getDeploymentPriority(other))

    # Returns the hosting Machine for the ServiceNode. It must be overriden
    # for nodes where they depend on an other service, and the hosting machine
    # is the other service's hosting machine
    def getHostingMachine(self):
        elementConnections = ElementConnection.objects.filter(
            Q(target=self) | Q(source=self))

        for connection in elementConnections:
            if isinstance(connection.target.cast(), Machine):
                return connection.target.cast()
            if isinstance(connection.source.cast(), Machine):
                return connection.source.cast()

        raise PermissionDenied

    # Return the deployment priority. The nodes are sorted by this attribute
    # and deployed in that order
    def getDeploymentPriority(self):
        return 0

    # Generate the salt commands which are needed to deploy the service
    def generateSaltCommands(self):
        raise PermissionDenied


class WordpressNode(ServiceNode):
    # DB related fields
    databaseName = models.TextField(default="")
    databaseUser = models.TextField(default="")
    databasePass = models.TextField(default="")

    # Admin user for the
    adminUsername = models.TextField(default="")
    adminPassword = models.TextField(default="")
    adminEmail = models.TextField(default="")

    # site related fields
    siteTitle = models.TextField(default="")
    siteUrl = models.TextField(default="")

    @staticmethod
    def clone():
        return WordpressNode()

    def getDataDictionary(self):
        element_data = ServiceNode.getDataDictionary(self)
        self_data = {'database-name': self.databaseName,
                     'database-user': self.databaseUser,
                     'database-pass': self.databasePass,
                     'admin-username': self.adminUsername,
                     'admin-password': self.adminPassword,
                     'admin-email': self.adminEmail,
                     'site-title': self.siteTitle,
                     'site-url': self.siteUrl}

        element_data.update(self_data)
        return element_data

    def fromDataDictionary(self, data):
        ServiceNode.fromDataDictionary(self, data)
        self.databaseName = data['database-name']
        self.databaseUser = data['database-user']
        self.databasePass = data['database-pass']
        self.adminUsername = data['admin-username']
        self.adminPassword = data['admin-password']
        self.adminEmail = data['admin-email']
        self.siteTitle = data['site-title']
        self.siteUrl = data['site-url']

    @staticmethod
    def getInformation():
        superInformation = ServiceNode.getInformation()
        ownInformation = {'database-name':
                          WordpressNode._meta.get_field(
                              'databaseName').get_internal_type(),
                          'database-user': WordpressNode._meta.get_field('databaseUser').get_internal_type(),
                          'database-pass': WordpressNode._meta.get_field('databasePass').get_internal_type(),
                          'admin-username': WordpressNode._meta.get_field('adminUsername').get_internal_type(),
                          'admin-password': WordpressNode._meta.get_field('adminPassword').get_internal_type(),
                          'admin-email': WordpressNode._meta.get_field('adminEmail').get_internal_type(),
                          'site-title': WordpressNode._meta.get_field('siteTitle').get_internal_type(),
                          'site-url': WordpressNode._meta.get_field('siteUrl').get_internal_type()}

        ownInformation.update(superInformation)
        return ownInformation

    def checkDependenciesAndAttributes(self):
        errorMessages = ServiceNode.checkDependenciesAndAttributes(self)

        if not self.databaseName:
            errorMessages.append(createErrorMessage(
                ugettext("Database name is not set"), "WordPress", self.name))
        if not self.databaseUser:
            errorMessages.append(createErrorMessage(
                ugettext("Database username is not set"), "WordPress", self.name))
        if not self.databasePass:
            errorMessages.append(createErrorMessage(
                ugettext("Database password is not set"), "WordPress", self.name))
        if not self.adminUsername:
            errorMessages.append(createErrorMessage(
                ugettext("Administrator's username is not set"), "WordPress", self.name))
        if not self.adminPassword:
            errorMessages.append(createErrorMessage(
                ugettext("Administrator's password is not set"), "WordPress", self.name))
        if not self.adminEmail:
            errorMessages.append(createErrorMessage(
                ugettext("Administrator's email is not set"), "WordPress", self.name))
        if not self.siteTitle:
            errorMessages.append(createErrorMessage(
                ugettext("Site's title is not set"), "WordPress", self.name))
        if not self.siteUrl:
            errorMessages.append(createErrorMessage(
                ugettext("Site's url is not set"), "WordPress", self.name))

        if not self.checkDependecy(MySQLNode):
            errorMessages.append(createErrorMessage(
                ugettext("No MySQL server connected to service"), "WordPress", self.name))

        if not self.checkDependecy(ApacheNode):
            errorMessages.append(createErrorMessage(
                ugettext("No Apache webserver connected to service"), "WordPress", self.name))

        return errorMessages

    def getHostingMachine(self):

        apacheNode = self.checkDependecy(ApacheNode)
        if not apacheNode:
            raise PermissionDenied

        hostingMachine = apacheNode.getHostingMachine()
        if not hostingMachine:
            raise PermissionDenied

        return hostingMachine

    @staticmethod
    def getDeploymentPriority(self):
        return 1

    def generateSaltCommands(self):
        mysqlNode = self.checkDependecy(MySQLNode)
        apacheNode = self.checkDependecy(ApacheNode)

        if not mysqlNode:
            raise PermissionDenied
        if not apacheNode:
            raise PermissionDenied

        installPhpCommand = apacheNode.makeInstallPhpCommand()
        restartApacheCommand = apacheNode.makeRestartCommand()
        createMySQLDatabaseCommand = mysqlNode.makeCreateDatabaseCommand(
            self.databaseName)
        createMySQLUserCommand = mysqlNode.makeCreateUserCommand(
            self.databaseUser, self.databasePass, self.databaseName)

        installWordpressCommand = SaltCommand()
        installWordpressCommand.hostname = self.getHostingMachine().hostname
        installWordpressCommand.command = "wordpress"
        installWordpressCommand.parameters = {'wordpress':
                                              {'cli':
                                               {'source':
                                                'https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar',
                                                'hash':
                                                'https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar.sha512'},
                                                  'lookup': {'docroot': '/var/www/html'},
                                                  'sites':
                                                  {'mysitename.com':
                                                   {'username': self.adminUsername,
                                                    'password': self.adminPassword,
                                                    'database': self.databaseName,
                                                    'dbhost': salthelper.getIpAddressOfMinion(mysqlNode.getHostingMachine().hostname),
                                                    'dbuser': self.databaseUser,
                                                    'dbpass': self.databasePass,
                                                    'url': self.siteUrl,
                                                    'title': self.siteTitle,
                                                    'email': self.adminEmail}}}}

        installMySqlClientCommand = SaltCommand()
        installMySqlClientCommand.hostname = self.getHostingMachine().hostname
        installMySqlClientCommand.command = "mysql.client"

        self.generatedCommands.append(installPhpCommand)
        self.generatedCommands.append(restartApacheCommand)
        self.generatedCommands.append(installMySqlClientCommand)
        self.generatedCommands.append(createMySQLDatabaseCommand)
        self.generatedCommands.append(createMySQLUserCommand)
        self.generatedCommands.append(installWordpressCommand)


class WebServerNode(ServiceNode):

    @staticmethod
    def getDeploymentPriority(self):
        return 10

    def checkDependenciesAndAttributes(self):
        errorMessages = ServiceNode.checkDependenciesAndAttributes(self)

        if not self.checkDependecy(Machine):
            errorMessages.append(createErrorMessage(ugettext("Machine is not connected"), "WebServer", self.name))

        return errorMessages


class ApacheNode(WebServerNode):

    @staticmethod
    def clone():
        return ApacheNode()

    def generateSaltCommands(self):
        saltCommand = SaltCommand()
        saltCommand.hostname = self.getHostingMachine().hostname
        saltCommand.command = "apache"

        self.generatedCommands.append(saltCommand)

    def makeInstallPhpCommand(self):
        saltCommand = SaltCommand()
        saltCommand.hostname = self.getHostingMachine().hostname
        saltCommand.command = "php-simple"

        return saltCommand

    def makeRestartCommand(self):
        saltCommand = SaltCommand()
        saltCommand.hostname = self.getHostingMachine().hostname
        saltCommand.command = "apache.restart"

        return saltCommand


class NginxNode(WebServerNode):

    @staticmethod
    def clone():
        return NginxNode()

    def generateSaltCommands(self):
        saltCommand = SaltCommand()
        saltCommand.hostname = self.getHostingMachine().hostname
        saltCommand.command = "nginx"

        self.generatedCommands.append(saltCommand)


class DatabaseNode(ServiceNode):
    adminPassword = models.CharField(max_length=50)

    def getDataDictionary(self):
        element_data = ServiceNode.getDataDictionary(self)
        self_data = {'admin_password': self.adminPassword}

        element_data.update(self_data)
        return element_data

    def fromDataDictionary(self, data):
        ServiceNode.fromDataDictionary(self, data)
        self.adminPassword = data['admin_password']

    def checkDependenciesAndAttributes(self):
        errorMessages = ServiceNode.checkDependenciesAndAttributes(self)

        if not self.adminPassword:
            errorMessages.append(createErrorMessage(
                ugettext("No admin password set"), "Database", self.name))

        if not self.checkDependecy(Machine):
            errorMessages.append(createErrorMessage(
                ugettext("No machine connected"), "Database", self.name))

        return errorMessages

    @staticmethod
    def getInformation():
        superInformation = ServiceNode.getInformation()
        ownInformation = {'admin_password': DatabaseNode._meta.get_field(
            'adminPassword').get_internal_type()}
        ownInformation.update(superInformation)
        return ownInformation

    @staticmethod
    def getDeploymentPriority(self):
        return 10


class PostgreSQLNode(DatabaseNode):

    @staticmethod
    def clone():
        return PostgreSQLNode()

    def generateSaltCommands(self):
        saltCommand = SaltCommand()
        saltCommand.hostname = self.getHostingMachine().hostname
        saltCommand.command = "postgresql"

        self.generatedCommands.append(saltCommand)


class MySQLNode(DatabaseNode):

    @staticmethod
    def clone():
        return MySQLNode()

    # Generate SaltCommand for database creation on the current MySQL instance
    def makeCreateDatabaseCommand(self, databaseName):
        saltCommand = SaltCommand()
        saltCommand.hostname = self.getHostingMachine().hostname
        saltCommand.command = "mysql.database"
        saltCommand.parameters = {'mysql': {
            'server': {'root_password': self.adminPassword}, 'database': [databaseName]}}
        return saltCommand

    # Generate SaltCommand for user creation on the current MySQL instance
    def makeCreateUserCommand(self, databaseUser, databasePass, grantPrivilageDatabase):
        saltCommand = SaltCommand()
        saltCommand.hostname = self.getHostingMachine().hostname
        saltCommand.command = "mysql.user"
        databaseGrants = [{'database': '*', 'grants': ['all privileges']}]
        if isinstance(grantPrivilageDatabase, list):
            for dbAccess in grantPrivilageDatabase:
                databaseGrants.append(
                    {'database': dbAccess, 'grants': ['all privileges']})
        else:
            databaseGrants.append(
                {'database': grantPrivilageDatabase, 'grants': ['all privileges']})

        saltCommand.parameters = {'mysql': {
            'server': {
                'root_password': self.adminPassword
            },
            'user': {
                databaseUser:
                {'password': databasePass,
                 'host': '%',
                 'databases': databaseGrants
                 }}}}
        return saltCommand

    def generateSaltCommands(self):
        saltCommand = SaltCommand()
        saltCommand.hostname = self.getHostingMachine().hostname
        saltCommand.command = "mysql.server"
        saltCommand.parameters = {
            'mysql': {'server': {'root_password': self.adminPassword, 'mysqld': {'bind-address': '0.0.0.0'}}}}

        self.generatedCommands.append(saltCommand)
