def get_node(instance):
    ''' Select a node for an hosting an instance
    based on requirements.
    '''
    # Return first Node or None
    from vm.models import Node
    try:
        return Node.objects.all()[0]
    except:
        return None
