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

from __future__ import absolute_import
from django.conf.urls import url, patterns

from occi.views import (
    QueryInterface, ComputeInterface, VmInterface, OsTplInterface,
    StorageInterface, DiskInterface, StorageLinkInterface,
    NetworkInterfaceView, VlanInterface,
    CIRCLEInterface,
)

urlpatterns = patterns(
    '',
    url(r'^-/$', QueryInterface.as_view(), name="occi.query"),
    url(r'^compute/$', ComputeInterface.as_view(), name="occi.compute"),
    url(r'^os_tpl/$', OsTplInterface.as_view(), name="occi.os_tpl"),
    url(r'^vm/(?P<pk>\d+)/?$', VmInterface.as_view(), name="occi.vm"),

    url(r'^storage/$', StorageInterface.as_view(), name="occi.storage"),
    url(r'^storage/(?P<pk>\d+)/?$', DiskInterface.as_view(), name="occi.disk"),

    url(r'^link/storagelink/$', StorageLinkInterface.as_view()),
    url(r'^link/storagelink/vm_(?P<vm_pk>\d+)_storage_(?P<disk_pk>\d+)/?$',
        StorageLinkInterface.as_view(), name="occi.storagelink"),

    url(r'^network2/?$', NetworkInterfaceView.as_view(), ),
    url(r'^network/(?P<vid>\d+)/?$', VlanInterface.as_view(), ),

    url(r'^link/networkinterface/$', CIRCLEInterface.as_view()),
    url(r'^link/networkinterface/'
        'vm_(?P<vm_pk>\d+)_network_(?P<vlan_vid>\d+)/?$',
        CIRCLEInterface.as_view(), name="occi.networkinterface"),
)
