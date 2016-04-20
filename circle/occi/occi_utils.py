"""" Utilities for the OCCI implementation of CIRCLE """

from django.http import JsonResponse, HttpResponse
import json


class OcciResourceInstanceNotExist(Exception):
    def __init__(self):
        message = "The resource instance does not exist."
        super(OcciResourceInstanceNotExist, self).__init__(message)
        self.response = JsonResponse({"error": message}, status=404,
                                     charset="utf-8")


class OcciActionInvocationError(Exception):
    def __init__(self, *args, **kwargs):
        message = kwargs.get("message", "Could not invoke action.")
        super(OcciActionInvocationError, self).__init__(message)
        self.response = JsonResponse({"error": message}, status=400,
                                     charset="utf-8")


class OcciResponse(HttpResponse):
    """ A response class with its occi headers set """
    # TODO: setting occi specific headers
    def init(self, data, response_type, *args, **kwargs):
        if response_type == "json":
            data = json.dumps(data)
        super(OcciResponse, self).__init__(data, status=418)
        if response_type == "json":
            self["Content-Type"] = "application/json"
        else:
            self["Content-Type"] = "text/plain"
        self["Server"] = "OCCI/1.2"


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
