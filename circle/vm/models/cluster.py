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

from __future__ import absolute_import, unicode_literals
from logging import getLogger
from django.db.models import (
    CharField, permalink
)
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from requests import ConnectionError

from common.operations import OperatedMixin
from pyVim.connect import SmartConnect, Disconnect
import pyVmomi
from pyVmomi import vim, vmodl

logger = getLogger(__name__)


def collect_properties(service_instance, view_ref, obj_type, path_set=None,
                       include_mors=False):
    """
    Collect properties for managed objects from a view ref

    Check the vSphere API documentation for example on retrieving
    object properties:

        - http://goo.gl/erbFDz

    Args:
        si          (ServiceInstance): ServiceInstance connection
        view_ref (pyVmomi.vim.view.*): Starting point of inventory navigation
        obj_type      (pyVmomi.vim.*): Type of managed object
        path_set               (list): List of properties to retrieve
        include_mors           (bool): If True include the managed objects
                                       refs in the result

    Returns:
        A list of properties for the managed objects

    """
    collector = service_instance.content.propertyCollector

    # Create object specification to define the starting point of
    # inventory navigation
    obj_spec = pyVmomi.vmodl.query.PropertyCollector.ObjectSpec()
    obj_spec.obj = view_ref
    obj_spec.skip = True

    # Create a traversal specification to identify the path for collection
    traversal_spec = pyVmomi.vmodl.query.PropertyCollector.TraversalSpec()
    traversal_spec.name = 'traverseEntities'
    traversal_spec.path = 'view'
    traversal_spec.skip = False
    traversal_spec.type = view_ref.__class__
    obj_spec.selectSet = [traversal_spec]

    # Identify the properties to the retrieved
    property_spec = pyVmomi.vmodl.query.PropertyCollector.PropertySpec()
    property_spec.type = obj_type

    if not path_set:
        property_spec.all = True

    property_spec.pathSet = path_set

    # Add the object and property specification to the
    # property filter specification
    filter_spec = pyVmomi.vmodl.query.PropertyCollector.FilterSpec()
    filter_spec.objectSet = [obj_spec]
    filter_spec.propSet = [property_spec]

    # Retrieve properties
    props = collector.RetrieveContents([filter_spec])

    data = []
    for obj in props:
        properties = {}
        for prop in obj.propSet:
            properties[prop.name] = prop.val

        if include_mors:
            properties['obj'] = obj.obj

        data.append(properties)
    return data


def get_container_view(service_instance, obj_type, container=None):
    """
    Get a vSphere Container View reference to all objects of type 'obj_type'

    It is up to the caller to take care of destroying the View when no longer
    needed.

    Args:
        obj_type (list): A list of managed object types

    Returns:
        A container view ref to the discovered managed objects

    """
    if not container:
        container = service_instance.content.rootFolder

    view_ref = service_instance.content.viewManager.CreateContainerView(
        container=container,
        type=obj_type,
        recursive=True
    )
    return view_ref


class Cluster(OperatedMixin, TimeStampedModel):
    """A VMware cluster.
    """
    name = CharField(max_length=50, unique=True,
                     verbose_name=_('name'),
                     help_text=_('Human readable name of cluster.'))
    address = CharField(max_length=200,
                        verbose_name=_('address'),
                        help_text=_('The address of the vCenter.'))

    username = CharField(max_length=200,
                         verbose_name=_('username'),
                         help_text=_('The username used for the connection.'),
                         default='')

    password = CharField(max_length=200,
                         verbose_name=_('password'),
                         help_text=_('The password used for the connection.'),
                         default='')

    class Meta:
        app_label = 'vm'
        db_table = 'vm_cluster'

    @permalink
    def get_absolute_url(self):
        return 'dashboard.views.cluster-detail', None, {'pk': self.id}

    def get_list_of_vms(self):

        # return [
        #     {
        #         'uuid': "5020222b-4d02-fe42-c630-af8325b384f9",
        #         'name': "unmanaged_vm",
        #         'cpu': 2,
        #         'memory': 2048,
        #         'state': "poweredOn",
        #         'os': "linux",
        #         'cluster_pk': 1,
        #     },
        #  ], [
        #     {
        #         'uuid': "5020222b-4d02-ce42-c630-af8325b384f9",
        #         'name': "managed_vm",
        #         'cpu': 2,
        #         'memory': 2048,
        #         'state': "poweredOn",
        #         'os': "linux",
        #         'time_of_expiration': "12/31/2015",
        #         'cluster_pk': 1,
        #     },
        #  ], [
        #     {
        #         'uuid': "5020222b-4d02-de42-c630-af8325b384f9",
        #         'name': "deleted_vm",
        #         'cluster_pk': 1,
        #     },
        #  ], None

        try:
            unmanaged_vm_list = []
            managed_vm_list = []
            deleted_vm_list = []

            si = SmartConnect(host=self.address,
                              user=self.username,
                              pwd=self.password,
                              port=443)

            # the info to acquire from each vm
            vm_properties = ["name", "config.instanceUuid", "config.hardware.numCPU",
                             "config.hardware.memoryMB", "summary.runtime.powerState",
                             "config.guestFullName"]

            view = get_container_view(si, obj_type=[vim.VirtualMachine])
            vm_data_from_vcenter = collect_properties(si, view_ref=view,
                                                      obj_type=vim.VirtualMachine,
                                                      path_set=vm_properties,
                                                      include_mors=True)

            from vm.models import VMwareVMInstance

            list_of_vcenter_vm_uuids = []

            for curr_vcenter_vm in vm_data_from_vcenter:
                list_of_vcenter_vm_uuids.append(curr_vcenter_vm["config.instanceUuid"])

                state = {
                    "poweredOn": "powered on",
                    "poweredOff": "powered off",
                    "suspended": "suspended"
                }.get(curr_vcenter_vm["summary.runtime.powerState"], "unknown")

                vm_info = {
                    'uuid':       curr_vcenter_vm["config.instanceUuid"],
                    'name':       curr_vcenter_vm["name"],
                    'cpu':        curr_vcenter_vm["config.hardware.numCPU"],
                    'memory':     curr_vcenter_vm["config.hardware.memoryMB"],
                    'state':      state,
                    'os':         curr_vcenter_vm["config.guestFullName"],
                    'cluster_pk': self.pk,
                }

                if VMwareVMInstance.objects.filter(instanceUUID=curr_vcenter_vm["config.instanceUuid"]).count() == 0:
                    # vm is not managed

                    unmanaged_vm_list.extend([vm_info])
                else:
                    # this vm is managed
                    # we may need to update our info in the database

                    curr_vm = VMwareVMInstance.objects.get(instanceUUID=curr_vcenter_vm["config.instanceUuid"])
                    curr_vm.name = vm_info["name"]
                    curr_vm.cpu_cores = vm_info["cpu"]
                    curr_vm.memory = vm_info["memory"]
                    curr_vm.operating_system = vm_info["os"]
                    curr_vm.save()

                    vm_info["owner"] = curr_vm.owner.username

                    managed_vm_list.extend([vm_info])

            Disconnect(si)

            for curr_managed_vm in VMwareVMInstance.objects.all():
                if curr_managed_vm.instanceUUID not in list_of_vcenter_vm_uuids:
                    vm_info = {
                        'uuid':       curr_managed_vm.instanceUUID,
                        'name':       curr_managed_vm.name,
                        'cpu':        curr_managed_vm.cpu_cores,
                        'memory':     curr_managed_vm.memory_size,
                        'os':         curr_managed_vm.operating_system,
                        'cluster_pk': self.pk,
                        'owner':      curr_managed_vm.owner.username,
                    }

                    deleted_vm_list.extend([vm_info])

            return unmanaged_vm_list, managed_vm_list, deleted_vm_list, None
        except ConnectionError:
            return None, None, None, "Connection to the cluster failed. Please check the connection settings."
        except vim.fault.InvalidLogin as e:
            return None, None, None, e.msg

    def get_vm_details_by_uuid(self, uuid):
        try:
            si = SmartConnect(host=self.address,
                              user=self.username,
                              pwd=self.password,
                              port=443)

            search_index = si.content.searchIndex
            vm = search_index.FindByUuid(None, uuid, True, True)

            state = {
                    "poweredOn": "powered on",
                    "poweredOff": "powered off",
                    "suspended": "suspended"
                }.get(vm.summary.runtime.powerState, "unknown")

            vm_info = {
                'uuid': vm.summary.config.instanceUuid,
                'name': vm.summary.config.name,
                'cpu': vm.summary.config.numCpu,
                'memory': vm.summary.config.memorySizeMB,
                'state': state,
                'os': vm.summary.config.guestFullName,
            }

            Disconnect(si)

            return vm_info

        except ConnectionError:
            return None, "Connection to the cluster failed. Please check the connection settings."
        except vim.fault.InvalidLogin as e:
            return None, e.msg

    def __unicode__(self):
        return self.name
