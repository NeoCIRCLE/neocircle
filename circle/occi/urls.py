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

from occi.views import QueryInterface, ComputeInterface, VmInterface

urlpatterns = patterns(
    '',
    url(r'^-/$', QueryInterface.as_view(), name="occi.query"),
    url(r'^compute/$', ComputeInterface.as_view(), name="occi.compute"),
    url(r'^vm/(?P<pk>\d+)/$', VmInterface.as_view(), name="occi.vm"),
)
