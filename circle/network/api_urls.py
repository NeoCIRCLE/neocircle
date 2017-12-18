# Copyright 2017 Budapest University of Technology and Economics (BME IK)
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
from rest_framework import routers

from . import api_views


router = routers.DefaultRouter()
router.register('blacklist', api_views.BlacklistViewSet)
router.register('domains', api_views.DomainViewSet)
router.register('firewalls', api_views.FirewallViewSet)
router.register('groups', api_views.GroupViewSet)
router.register('hosts', api_views.HostViewSet)
router.register('records', api_views.RecordViewSet)
router.register('rules', api_views.RuleViewSet)
router.register('switchports', api_views.SwitchPortViewSet)
router.register('vlans', api_views.VlanViewSet)
router.register('vlangroups', api_views.VlanGroupViewSet)


urlpatterns = router.urls
