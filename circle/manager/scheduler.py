def get_node(instance, nodes):
    ''' Select a node for hosting an instance based on its requirements.
    '''
    # Return first Node or None
    try:
        return nodes[0]
    except:
        return None
