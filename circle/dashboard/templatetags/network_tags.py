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

from django import template

register = template.Library()


LINKABLE_PORTS = {80: "http", 8080: "http", 443: "https", 21: "ftp"}


@register.simple_tag(name="display_portforward4")
def display_pf4(ports):
    return display_pf(ports, 'ipv4')


@register.simple_tag(name="display_portforward6")
def display_pf6(ports):
    return display_pf(ports, 'ipv6')


def display_pf(ports, proto):
    data = ports[proto]

    if ports['private'] in LINKABLE_PORTS.keys():
        href = "%s:%d" % (data['host'], data['port'])
        return '<a href="%s://%s">%s</a>' % (
            LINKABLE_PORTS.get(ports['private']), href, href)
    return "%s:%d" % (data['host'], data['port'])
