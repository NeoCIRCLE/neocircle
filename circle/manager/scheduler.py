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

from logging import getLogger

from django.db.models import Sum

logger = getLogger(__name__)


class NotEnoughMemoryException(Exception):

    def __init__(self, message=None):
        if message is None:
            message = "No node has enough memory to accomodate the guest."

        Exception.__init__(self, message)


class TraitsUnsatisfiableException(Exception):

    def __init__(self, message=None):
        if message is None:
            message = "No node can satisfy all required traits of the guest."

        Exception.__init__(self, message)


def select_node(instance, nodes):
    ''' Select a node for hosting an instance based on its requirements.
    '''
    # check required traits
    nodes = [n for n in nodes
             if n.enabled and n.online
             and has_traits(instance.req_traits.all(), n)]
    if not nodes:
        logger.warning('select_node: no usable node for %s', unicode(instance))
        raise TraitsUnsatisfiableException()

    # check required RAM
    nodes = [n for n in nodes if has_enough_ram(instance.ram_size, n)]
    if not nodes:
        logger.warning('select_node: no enough RAM for %s', unicode(instance))
        raise NotEnoughMemoryException()

    # sort nodes first by processor usage, then priority
    nodes.sort(key=lambda n: n.priority, reverse=True)
    nodes.sort(key=free_cpu_time, reverse=True)
    result = nodes[0]

    logger.info('select_node: %s for %s', unicode(result), unicode(instance))
    return result


def has_traits(traits, node):
    """True, if the node has all specified traits; otherwise, false.
    """
    traits = set(traits)
    return traits.issubset(node.traits.all())


def has_enough_ram(ram_size, node):
    """True, if the node has enough memory to accomodate a guest requiring
       ram_size mebibytes of memory; otherwise, false.
    """
    try:
        total = node.ram_size
        used = (node.ram_usage / 100) * total
        unused = total - used

        overcommit = node.ram_size_with_overcommit
        reserved = node.instance_set.aggregate(r=Sum('ram_size'))['r'] or 0
        free = overcommit - reserved

        return ram_size < unused and ram_size < free
    except TypeError as e:
        logger.warning('Got incorrect monitoring data for node %s. %s',
                       unicode(node), unicode(e))
        return False


def free_cpu_time(node):
    """Get an indicator number for idle processor time on the node.

    Higher values indicate more idle time.
    """
    try:
        activity = node.cpu_usage / 100
        inactivity = 1 - activity
        cores = node.num_cores
        return cores * inactivity
    except TypeError as e:
        logger.warning('Got incorrect monitoring data for node %s. %s',
                       unicode(node), unicode(e))
        return False  # monitoring data is incorrect
