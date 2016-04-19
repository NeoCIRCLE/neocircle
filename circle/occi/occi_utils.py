"""" Utilities for the OCCI implementation of CIRCLE """


def set_optional_attributes(self, optional_attributes, kwargs):
    """ Sets the optional arguments of an instance.
        If the kwargs dictionary has any values with the keys defined in
        the optional_attributes tuple, it sets them on the instance """
    for k, v in kwargs.iteritems():
        if k in optional_attributes:
            setattr(self, k, v)


def serialize_attributes(attributes):
    """ Creates a list of attributes, that are serializable to json from
        a list of Attribute class objects. """
    atrs = []
    for attribute in attributes:
        atrs.append(attribute.render_as_json())
    return atrs


def action_list_for_resource(actions):
    """ Creates a list of actions for Resource object rendering """
    acts = []
    for action in actions:
        acts.append(action.scheme + action.term)
    return acts
