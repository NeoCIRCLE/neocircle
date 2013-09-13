def get_node(instance):
    ''' Select a node for an hosting an instance
    based on requirements.
    '''
    # Return first Node or None
    models = __import__('vm.models')
    try:
        return models.models.Node.objects.all()[0]
    except:
        return None
