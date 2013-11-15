def get_node(instance, nodes):
    ''' Select a node for hosting an instance based on its requirements.
    '''
    # Return first Node or None
    try:
        req_traits = set(instance.req_traits.all())
        nodes = [n for n in nodes if req_traits.issubset(n.traits.all())]
        return nodes[0]
    except:
        return None
