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

from manager.mancelery import celery


@celery.task(name='firewall.reload_dns')
def reload_dns(data):
    pass


@celery.task(name='firewall.reload_firewall')
def reload_firewall(data4, data6):
    pass


@celery.task(name='firewall.reload_firewall_vlan')
def reload_firewall_vlan(data):
    pass


@celery.task(name='firewall.reload_dhcp')
def reload_dhcp(data):
    pass


@celery.task(name='firewall.reload_blacklist')
def reload_blacklist(data):
    pass


@celery.task(name='firewall.get_dhcp_clients')
def get_dhcp_clients(data):
    pass
