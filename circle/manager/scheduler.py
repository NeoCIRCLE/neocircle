from vm.models import Node

def get_node(instance):
    ''' Select a node for an hosting an instance
    based on requirements.
    '''
    # Return first Node or None
    try:
        return Node.objects.all()[0]
    except:
        return None
