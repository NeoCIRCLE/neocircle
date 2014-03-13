from django.db.models import Sum


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
             if n.enabled and has_traits(instance.req_traits.all(), n)]
    if not nodes:
        raise TraitsUnsatisfiableException()

    # check required RAM
    nodes = [n for n in nodes if has_enough_ram(instance.ram_size, n)]
    if not nodes:
        raise NotEnoughMemoryException()

    # sort nodes first by processor usage, then priority
    nodes.sort(key=lambda n: n.priority, reverse=True)
    nodes.sort(key=free_cpu_time, reverse=True)

    return nodes[0]


def has_traits(traits, node):
    """True, if the node has all specified traits; otherwise, false.
    """
    traits = set(traits)
    return traits.issubset(node.traits.all())


def has_enough_ram(ram_size, node):
    """True, if the node has enough memory to accomodate a guest requiring
       ram_size mebibytes of memory; otherwise, false.
    """
    total = node.ram_size
    used = (node.ram_usage / 100) * total
    unused = total - used

    overcommit = node.ram_size_with_overcommit
    reserved = node.instance_set.aggregate(r=Sum('ram_size'))['r'] or 0
    free = overcommit - reserved

    return ram_size < unused and ram_size < free


def free_cpu_time(node):
    """Get an indicator number for idle processor time on the node.

    Higher values indicate more idle time.
    """
    activity = node.cpu_usage / 100
    inactivity = 1 - activity
    cores = node.num_cores
    return cores * inactivity
