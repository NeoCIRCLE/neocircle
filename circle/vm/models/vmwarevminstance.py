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

from django.contrib.auth.models import User
from django.db.models import (
    CharField, ForeignKey, permalink, DateTimeField, IntegerField)
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
from requests import ConnectionError

from common.operations import OperatedMixin
from vm.models import Cluster

logger = getLogger(__name__)


class VMwareVMInstance(OperatedMixin, TimeStampedModel):
    """A VMware virtual machine instance.
    """
    name = CharField(max_length=50, unique=True,
                     verbose_name=_('name'),
                     help_text=_('The name of the virtual machine.'))
    instanceUUID = CharField(max_length=200,
                             verbose_name=_('instanceUUID'),
                             help_text=_('A unique identifier of the VM.'),
                             unique=True)

    time_of_expiration = DateTimeField(blank=True, default=None, null=True,
                                       verbose_name=_('time of expiration'),
                                       help_text=_("The time, when the virtual machine"
                                                   " will expire."))
    cluster = ForeignKey(Cluster, null=False)

    owner = ForeignKey(User, null=False)

    operating_system = CharField(max_length=200,
                                 verbose_name=_('operating system'),
                                 help_text=_('The OS of the VM.'),
                                 unique=True)

    cpu_cores = IntegerField(help_text=_('The number of CPU cores in the VM.'))

    memory_size = IntegerField(help_text=_('The amount of memory (MB) in the VM.'))

    class Meta:
        app_label = 'vm'
        db_table = 'vm_vmware_vminstance'
        verbose_name = 'VMware virtual machine instance'

    @permalink
    def get_absolute_url(self):
        return 'dashboard.views.vmwarevminstance-detail', None, {'pk': self.id}

    def __unicode__(self):
        return self.name

    def shutdown_vm(self):
        try:
            si = SmartConnect(host=self.cluster.address,
                              user=self.cluster.username,
                              pwd=self.cluster.password,
                              port=443)

            search_index = si.content.searchIndex
            vm = search_index.FindByUuid(None, self.instanceUUID, True, True)

            vm.ShutdownGuest()
            Disconnect(si)

        except ConnectionError:
            pass
        except vim.fault.InvalidLogin as e:
            pass
        except vim.fault.ToolsUnavailable:
            pass

    def start_vm(self):
        try:
            si = SmartConnect(host=self.cluster.address,
                              user=self.cluster.username,
                              pwd=self.cluster.password,
                              port=443)

            search_index = si.content.searchIndex
            vm = search_index.FindByUuid(None, self.instanceUUID, True, True)

            vm.PowerOnVM_Task()
            Disconnect(si)

        except ConnectionError:
            pass
        except vim.fault.InvalidLogin as e:
            pass

    def restart_vm(self):
        try:
            si = SmartConnect(host=self.cluster.address,
                              user=self.cluster.username,
                              pwd=self.cluster.password,
                              port=443)

            search_index = si.content.searchIndex
            vm = search_index.FindByUuid(None, self.instanceUUID, True, True)

            vm.RebootGuest()
            Disconnect(si)

        except ConnectionError:
            pass
        except vim.fault.InvalidLogin as e:
            pass

    def suspend_vm(self):
        try:
            si = SmartConnect(host=self.cluster.address,
                              user=self.cluster.username,
                              pwd=self.cluster.password,
                              port=443)

            search_index = si.content.searchIndex
            vm = search_index.FindByUuid(None, self.instanceUUID, True, True)

            vm.StandbyGuest()
            Disconnect(si)

        except ConnectionError:
            pass
        except vim.fault.InvalidLogin as e:
            pass

    def get_vm_info(self):
        return self.cluster.get_vm_details_by_uuid(self.instanceUUID)

    def get_status_icon(self, state):
        return {
            'powered on': 'fa-play',
            'powered off': 'fa-stop',
            'suspended': 'fa-pause',
        }.get(state, 'fa-question')