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

from django.utils.translation import ugettext_noop

from common.models import HumanReadableException

logger = getLogger(__name__)


class SchedulerError(HumanReadableException):
    admin_message = None

    def __init__(self, params=None, level=None, **kwargs):
        kwargs.update(params or {})
        super(SchedulerError, self).__init__(
            level, self.message, self.admin_message or self.message,
            kwargs)


class NotEnoughMemoryException(SchedulerError):
    message = ugettext_noop(
        "The resources required for launching the virtual machine are not "
        "available currently. Please try again later.")

    admin_message = ugettext_noop(
        "The required free memory for launching the virtual machine is not "
        "available on any usable node currently. Please try again later.")


class TraitsUnsatisfiableException(SchedulerError):
    message = ugettext_noop(
        "No node can satisfy the required traits of the "
        "new virtual machine currently.")


def select_node(instance, nodes):
    ''' Select a node for hosting an instance based on its requirements.
    '''
    # check required traits
    nodes = [n for n in nodes
             if n.schedule_enabled and n.online and
             has_traits(instance.req_traits.all(), n)]
    if not nodes:
        logger.warning('select_node: no usable node for %s', unicode(instance))
        raise TraitsUnsatisfiableException()

    # check required RAM
    nodes = [n for n in nodes if has_enough_ram(instance.ram_size, n)]
    if not nodes:
        logger.warning('select_node: no enough RAM for %s', unicode(instance))
        raise NotEnoughMemoryException()

    # sort nodes first by sorting_key, then priority
    nodes.sort(key=lambda n: n.priority, reverse=True)
    nodes.sort(key=sorting_key, reverse=True)
    result = nodes[0]

    logger.info('select_node: %s for %s', unicode(result), unicode(instance))
    return result


def sorting_key(node):
    """Determines how valuable a node is for scheduling.
    """
    if free_cpu_time(node) < free_ram(node):
        return free_cpu_time(node)
    return free_ram(node)


def has_traits(traits, node):
    """True, if the node has all specified traits; otherwise, false.
    """
    traits = set(traits)
    return traits.issubset(node.traits.all())


def has_enough_ram(ram_size, node):
    """True, if the node has enough memory to accomodate a guest requiring
       ram_size mebibytes of memory; otherwise, false.
    """
    ram_size = ram_size * 1024 * 1024
    try:
        total = node.ram_size
        used = node.byte_ram_usage
        unused = total - used

        overcommit = node.ram_size_with_overcommit
        reserved = node.allocated_ram
        free = overcommit - reserved

        retval = ram_size < unused and ram_size < free

        logger.debug('has_enough_ram(%d, %s)=%s (total=%s unused=%s'
                     ' overcommit=%s free=%s free_ok=%s overcommit_ok=%s)',
                     ram_size, node, retval, total, unused, overcommit, free,
                     ram_size < unused, ram_size < free)
        return retval
    except TypeError as e:
        logger.exception('Got incorrect monitoring data for node %s. %s',
                         unicode(node), unicode(e))
        return False


def free_cpu_time(node):
    """Get an indicator number for idle processor time on the node.

    Higher values indicate more idle time.
    """
    try:
        free_cpu_percent = 1 - node.cpu_usage
        weight = node.cpu_weight
        weighted_value = free_cpu_percent * weight
        return weighted_value
    except TypeError as e:
        logger.warning('Got incorrect monitoring data for node %s. %s',
                       unicode(node), unicode(e))
        return False  # monitoring data is incorrect


def free_ram(node):
    """Get an indicator number for free RAM on the node.

    Higher value indicates more RAM.
    """
    try:
        free_ram_percent = 1 - node.ram_usage
        weight = node.ram_weight
        weighted_value = free_ram_percent * weight
        return weighted_value
    except TypeError as e:
        logger.exception('Got incorrect monitoring data for node %s. %s',
                         unicode(node), unicode(e))
        return 0
