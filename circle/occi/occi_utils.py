"""" Utilities for the OCCI implementation of CIRCLE """


def set_optional_attributes(self, optional_attributes, kwargs):
    """ Sets the optional arguments of an instance.
        If the kwargs dictionary has any values with the keys defined in
        the optional_attributes tuple, it sets them on the instance """
    for k, v in kwargs.iteritems():
        if k in optional_attributes:
            setattr(self, k, v)
