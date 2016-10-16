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
from django.db.models import Model, Q
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from taggit.managers import TaggableManager
from django.utils.translation import ugettext_lazy as _
from storage import OverwriteStorage
import os

# TODO: derive from object or keep the tricky base function calling?
# TODO: exceptions

SALTSTACK_STATE_FOLDER = "/srv/salt"


def replaceParameter(config, parameterToReplace, newValue):
    configEdited = config.replace(parameterToReplace, str(newValue))
    return configEdited


class Service(models.Model):
    SERVICE_STATUS_CHOICES = ((1, 'Draft'),
                              (2, 'Deployed'))

    user = models.ForeignKey(User)
    name = models.TextField(verbose_name="Name")
    status = models.CharField(
        choices=SERVICE_STATUS_CHOICES, max_length=1, default=1)

    def __unicode__(self):
        return self.name


class ElementCategory(models.Model):
    name = models.CharField(max_length=50)
    parent_category = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True)

    def __unicode__(self):
        return self.name

# Defines a model for ElementTemplates which are used to create real elements on the GUI
# Hold


class ElementTemplate(models.Model):
    name = models.CharField(max_length=50)
    logo = models.FileField(upload_to='setty/', storage=OverwriteStorage())
    description = models.TextField()
    compatibles = models.ManyToManyField('self', blank=True)
    category = models.ForeignKey(
        ElementCategory, on_delete=models.CASCADE, null=True)
    prototype = models.TextField(default="<SYNTAX ERROR>")

    def __unicode__(self):
        return self.name

# http://stackoverflow.com/questions/929029/how-do-i-access-the-child-classes-of-an-object-in-django-without-knowing-the-name/929982#929982
# Super base class to prevent messing the code in the controller
# it saves the type info to DB, and when the objects are queried, the cast method returns the real class
# not the base


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


class Element(InheritanceCastModel):
    display_id = models.TextField()
    position_left = models.FloatField()
    position_top = models.FloatField()
    anchor_number = models.PositiveSmallIntegerField()

    def getDisplayData(self):
        return {'displayId': self.display_id,
                'positionLeft': self.position_left,
                'positionTop': self.position_top,
                'anchorNumber': self.anchor_number}

    def setDisplayData(self, data):
        self.display_id = data["displayId"]
        self.position_left = data["positionLeft"]
        self.position_top = data["positionTop"]
        self.anchor_number = data["anchorNumber"]


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


class Machine(Element):  # As a real machine
    MACHINE_STATUS_CHOICES = (
        (1, 'Running'),
        (2, 'Unreachable'))

    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="service_id")
    hostname = models.TextField(null=False)  # also serves as salt-minion id
    alias = models.CharField(max_length=50)
    description = models.TextField(default="")
    status = models.CharField(choices=MACHINE_STATUS_CHOICES, max_length=1)

    def __unicode__(self):
        return "%s" % self.hostname

    @staticmethod
    def getInformation():
        return {'hostname': hostname.get_internal_type(),
                'alias': alias.get_internal_type(),
                'description': description.get_internal_type()}

    def getDataDictionary(self):
        element_data = self.getDisplayData()

        self_data = {'hostname': self.hostname,
                     'alias': self.alias,
                     'description': self.description}

        element_data.update(self_data)
        return element_data

    def fromDataDictionary(self, data):
        self.setDisplayData(data)
        self.hostname = data["hostname"]
        self.alias = data["alias"]
        self.description = data["description"]

    @staticmethod
    def clone():
        return Machine()


class ServiceNode(Element):
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, default=None)
    name = models.CharField(max_length=50)
    config_file = models.FileField(
        default=None, upload_to='setty/node_configs/', storage=OverwriteStorage())
    description = models.TextField(default="")
    machine = None  # for deploying
    generatedConfig = None

    def __unicode__(self):
        return "%s" % self.name

    def getDataDictionary(self):
        element_data = self.getDisplayData()

        self_data = {'name': self.name,
                     'description': self.description}

        element_data.update(self_data)
        return element_data

    def fromDataDictionary(self, data):
        self.setDisplayData(data)
        self.name = data['name']
        self.description = data['description']

    @staticmethod
    def getInformation():
        return {'name': ServiceNode._meta.get_field('name').get_internal_type(),
                'description': ServiceNode._meta.get_field('description').get_internal_type()}

    @staticmethod
    def clone():
        raise PermissionDenied

    def checkDependenciesAndAttributes(self):
        return []

    def checkDependecy(self, ObjOther):
        elementConnections = ElementConnection.objects.filter(
            Q(target=self) | Q(source=self))

        for connection in elementConnections:
            serviceNode = None
            if connection.target.cast() == self:
                if isinstance(connection.source.cast(), ObjOther):
                    return True
            elif connection.source.cast() == self:
                if isinstance(connection.target.cast(), ObjOther):
                    return True
        return False

    def __cmp__(self, other):
        return self.getDeploymentPriority(self).__cmp__(other.getDeploymentPriority(other))

    # functions for deployement
    def setMachineForDeploy(self, machine):
        self.machine = machine

    def getDeploymentPriority(self):
        return 0

    def generateConfigurationRecursively(self):
        raise PermissionDenied


class WordpressNode(ServiceNode):
    # DB related fields
    databaseListeningPort = models.PositiveIntegerField()
    databaseHost = models.TextField()
    databaseUser = models.TextField()
    databasePass = models.TextField()

    # admin user
    adminUsername = models.TextField()
    adminPassword = models.TextField()
    adminEmail = models.TextField()

    # site related fields
    siteTitle = models.TextField()
    siteUrl = models.TextField()

    def getDataDictionary(self):
        element_data = ServiceNode.getDataDictionary(self)
        self_data = {'database-listening-port': self.databaseListeningPort,
                     'database-host': self.databaseHost,
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
        self.databaseListeningPort = data['database-listening-port']
        self.databaseHost = data['database-host']
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
        ownInformation = {'use-ssl': WebServerNode._meta.get_field('useSSL').get_internal_type(),
                          'listeningport': WebServerNode._meta.get_field('listeningport').get_internal_type()}

        ownInformation = {'database-listening-port': WordpressNode._meta.get_field('databaseListeningPort').get_internal_type(),
                          'database-host': WordpressNode._meta.get_field('databaseHost').get_internal_type(),
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

        if self.databaseListeningPort == 0:
            errorMessages.append("LISTENING_PORT_NOT_SET")
        if not self.databaseHost:
            errorMessage.append("DATABASEHOST_NOT_SET")
        if not self.databaseUser:
            errorMessage.append("DATABASEUSER_NOT_SET")
        if not self.databasePass:
            errorMessage.append("DATABASEPASS_NOT_SET")
        if not self.adminUsername:
            errorMessage.append("ADMINUSERNAME_NOT_SET")
        if not self.adminPassword:
            errorMessage.append("ADMINPASSWORD_NOT_SET")
        if not self.adminEmail:
            errorMessage.append("ADMINEMAIL_NOT_SET")
        if not self.siteTitle:
            errorMessage.append("SITETITLE_NOT_SET")
        if not self.siteUrl:
            errorMessage.append("SITEURL_NOT_SET")

        if not self.checkDependecy(MySQLNode):
            errorMessage.append("NODE_NOT_CONNECTED")

        if not self.checkDependecy(WebServerNode):
            errorMessage.append("NODE_NOT_CONNECTED")

        return errorMessages

    @staticmethod
    def getDeploymentPriority(self):
        return 10

    def generateConfiguration(self, config=""):

        config = replaceParameter(
            config, r'%%DATABASE_LISTENING_PORT%%', self.databaseListeningPort)
        config = replaceParameter(
            config, r'%%DATABASE_HOST%%', self.databaseHost)
        config = replaceParameter(
            config, r'%%DATABASE_USER%%', self.databaseUser)
        config = replaceParameter(
            config, r'%%DATABASE_PASS%%', self.databasePass)
        config = replaceParameter(
            config, r'%%ADMIN_USERNAME%%', self.adminUsername)
        config = replaceParameter(
            config, r'%%ADMIN_PASSWORD%%', self.adminPassword)
        config = replaceParameter(config, r'%%ADMIN_EMAIL%%', self.adminEmail)
        config = replaceParameter(config, r'%%SITE_TITLE%%', self.siteTitle)
        config = replaceParameter(config, r'%%SITE_URL%%', self.siteUrl)

        return config


class WebServerNode(ServiceNode):
    useSSL = models.BooleanField(default=False)
    listeningPort = models.PositiveIntegerField()

    def getDataDictionary(self):
        element_data = ServiceNode.getDataDictionary(self)

        self_data = {'use-ssl': self.useSSL,
                     'listeningport': self.listeningPort}

        element_data.update(self_data)
        return element_data

    def fromDataDictionary(self, data):
        ServiceNode.fromDataDictionary(self, data)
        self.useSSL = data['use-ssl']
        self.listeningPort = data['listeningport']

    def checkDependenciesAndAttributes(self):
        errorMessages = ServiceNode.checkDependenciesAndAttributes(self)
        if self.listeningPort == 0:
            errorMessages.append("LISTENING_PORT_NOT_SET")

        if not self.checkDependecy(Machine):
            errorMessages.append("NO_MACHINE_CONNECTED")

        return errorMessages

    @staticmethod
    def getInformation():
        superInformation = ServiceNode.getInformation()
        ownInformation = {'use-ssl': WebServerNode._meta.get_field('useSSL').get_internal_type(),
                          'listeningport': WebServerNode._meta.get_field('listeningport').get_internal_type()}

        ownInformation.update(superInformation)
        return ownInformation

    @staticmethod
    def getDeploymentPriority(self):
        return 10

    def generateConfiguration(self, config=""):
        config = replaceParameter(config, r"%%USE_SSL%%", self.useSSL)
        config = replaceParameter(config,
                                  r"%%LISTENING_PORT%%", self.listeningPort)
        return config


class ApacheNode(WebServerNode):

    @staticmethod
    def clone():
        return ApacheNode()

    def generateConfigurationRecursively(self):
        config = str()
        exampleFilePath = os.path.join(
            SALTSTACK_STATE_FOLDER, "apache.example")
        with open(exampleFilePath, 'r') as configFile:
            config = configFile.read()
            config = WebServerNode.generateConfiguration(self, config)

        self.generatedConfig = "apache_%s.sls" % self.machine.hostname
        with open(os.path.join(SALTSTACK_STATE_FOLDER, self.generatedConfig), 'w') as generatedConfigFile:
            generatedConfigFile.write(config)

        configuredNodes = []
        configuredNodes.append(self)

        return configuredNodes


class NginxNode(WebServerNode):
    worker_connections = models.PositiveIntegerField()

    def getDataDictionary(self):
        element_data = WebServerNode.getDataDictionary(self)
        self_data = {'worker_connections': self.worker_connections}
        element_data.update(self_data)
        return element_data

    def fromDataDictionary(self, data):
        WebServerNode.fromDataDictionary(self, data)
        self.worker_connections = data['worker_connections']

    def checkDependenciesAndAttributes(self):
        errorMessages = WebServerNode.checkDependenciesAndAttributes(self)
        if self.worker_connections == 0:
            errorMessages.append("WORKER_CONNECTIONS_NOT_SET")

        return errorMessages

    @staticmethod
    def getInformation():
        superInformation = WebServerNode.getInformation()
        ownInformation = {'worker_connections': NginxNode._meta.get_field(
            'worker_connections').get_internal_type()}
        ownInformation.update(superInformation)
        return ownInformation

    @staticmethod
    def clone():
        return NginxNode()

    def generateConfigurationRecursively(self):
        config = str()
        exampleFilePath = os.path.join(SALTSTACK_STATE_FOLDER, "nginx.example")
        with open(exampleFilePath, 'r') as configFile:
            config = configFile.read()
            config = WebServerNode.generateConfiguration(self, config)
            config = replaceParameter(config,
                                      r"%%WORKER_CONNECTIONS%%", self.worker_connections)

        self.generatedConfig = "nginx_%s.sls" % self.machine.hostname
        with open(os.path.join(SALTSTACK_STATE_FOLDER, self.generatedConfig), 'w') as generatedConfigFile:
            generatedConfigFile.write(config)

        configuredNodes = []
        configuredNodes.append(self)

        return configuredNodes


class DatabaseNode(ServiceNode):
    adminUserName = models.CharField(max_length=50)
    adminPassword = models.CharField(max_length=50)
    listeningPort = models.PositiveIntegerField()

    def getDataDictionary(self):
        element_data = ServiceNode.getDataDictionary(self)
        self_data = {'admin_username': self.adminUserName,
                     'admin_password': self.adminPassword,
                     'listeningport':  self.listeningPort}

        element_data.update(self_data)
        return element_data

    def fromDataDictionary(self, data):
        ServiceNode.fromDataDictionary(self, data)
        self.adminUserName = data['admin_username']
        self.adminPassword = data['admin_password']
        self.listeningPort = data['listeningport']

    def checkDependenciesAndAttributes(self):
        errorMessages = ServiceNode.checkDependenciesAndAttributes(self)
        if not self.adminUserName:
            errorMessages.append("ADMIN_USER_NAME_NOT_SET")
        if not self.adminPassword:
            errorMessages.append("ADMIN_PASSWORD_NAME_NOT_SET")
        if self.listeningPort == 0:
            errorMessages.append("LISTENING_PORT_NOT_SET")

        if not self.checkDependecy(Machine):
            errorMessages.append("NO_MACHINE_CONNECTED")

        return errorMessages

    @staticmethod
    def getInformation():
        superInformation = ServiceNode.getInformation()
        ownInformation = {'admin_username': DatabaseNode._meta.get_field('adminUserName').get_internal_type(),
                          'admin_password': DatabaseNode._meta.get_field('adminPassword').get_internal_type(),
                          'listeningport':  DatabaseNode._meta.get_field('listeningPort').get_internal_type()}
        ownInformation.update(superInformation)
        return ownInformation

    @staticmethod
    def getDeploymentPriority(self):
        return 10

    def generateConfiguration(self, config=""):
        config = replaceParameter(config,
                                  r"%%ADMIN_USERNAME%%", self.adminUserName)
        config = replaceParameter(config,
                                  r"%%ADMIN_PASSWORD%%", self.adminUserName)
        config = replaceParameter(config,
                                  r'%%LISTENING_PORT%%', self.listeningPort)
        return config


class PostgreSQLNode(DatabaseNode):

    @staticmethod
    def clone():
        return PostgreSQLNode()

    def generateConfigurationRecursively(self):
        config = str()
        exampleFilePath = os.path.join(
            SALTSTACK_STATE_FOLDER, "postgres.example")
        with open(exampleFilePath, 'r') as configFile:
            config = configFile.read()
            config = DatabaseNode.generateConfiguration(self, config)

        self.generatedConfig = "postgres_%s.sls" % self.machine.hostname
        with open(os.path.join(SALTSTACK_STATE_FOLDER, self.generatedConfig), 'w') as generatedConfigFile:
            generatedConfigFile.write(config)

        return self


class MySQLNode(DatabaseNode):

    @staticmethod
    def clone():
        return MySQLNode()

    def generateConfigurationRecursively(self):
        config = str()
        exampleFilePath = os.path.join(SALTSTACK_STATE_FOLDER, "mysql.example")
        with open(exampleFilePath, 'r') as configFile:
            config = configFile.read()
            config = DatabaseNode.generateConfiguration(self, config)

        self.generatedConfig = "mysql_%s.sls" % self.machine.hostname
        with open(os.path.join(SALTSTACK_STATE_FOLDER, self.generatedConfig), 'w') as generatedConfigFile:
            generatedConfigFile.write(config)

        return self
