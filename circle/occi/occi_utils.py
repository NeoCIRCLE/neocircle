# Copyright 2017 Budapest University of Technology and Economics (BME IK)
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


"""" Utilities for the OCCI implementation of CIRCLE """

from django.http import HttpResponse
import json


class OcciException(Exception):
    """ The superclass for OCCI exceptions. It creates a response to be
        returned when an error occures. """

    def __init__(self, *args, **kwargs):
        message = kwargs.get("message", "An error occured.")
        status = kwargs.get("status", 400)
        super(OcciException, self).__init__(message)
        self.response = occi_response({"error": message}, status=status)


class OcciResourceInstanceNotExist(OcciException):
    """ An exception to be raised when a resource instance which has been
        asked for does not exist. """

    def __init__(self, *args, **kwargs):
        if "message" not in kwargs:
            kwargs["message"] = "The resource instance does not exist."
        super(OcciResourceInstanceNotExist, self).__init__(self, **kwargs)


class OcciActionInvocationError(OcciException):
    """ An exception to be raised when an action could not be invoked on
        an entity instance for some reason """

    def __init__(self, *args, **kwargs):
        if "message" not in kwargs:
            kwargs["message"] = "Could not invoke action."
        super(OcciActionInvocationError, self).__init__(self, **kwargs)


class OcciResourceCreationError(OcciException):
    """ An exception to be raised when a resource instance could not be
        created for a reason. """

    def __init__(self, *args, **kwargs):
        if "message" not in kwargs:
            kwargs["message"] = "Could not create resource instance."
        super(OcciResourceCreationError, self).__init__(self, **kwargs)


class OcciResourceDeletionError(OcciException):
    """ An exception to be raised when a resource instance could not be
        deleted for some reason. """

    def __init__(self, *args, **kwargs):
        if "message" not in kwargs:
            kwargs["message"] = "Could not delete resource instance."
        super(OcciResourceDeletionError, self).__init__(self, **kwargs)


class OcciRequestNotValid(OcciException):
    """ An exception to be raised when the request sent by the client is
        not valid for a reason. (e.g, wrong content type, etc.) """

    def __init__(self, *args, **kwargs):
        if "message" not in kwargs:
            kwargs["message"] = "The request is not valid."
        super(OcciRequestNotValid, self).__init__(self, **kwargs)


def occi_response(data, *args, **kwargs):
    """ This function returns a response with its headers set, like occi
        server. The content_type of the response is application/json
        by default. """
    status = kwargs.get("status", 200)
    # TODO: support for renderings other than json (e.g., text/plain)
    data = json.dumps(data)
    response = HttpResponse(data, charset="utf-8", status=status,
                            content_type="application/json; charset=utf-8")
    # TODO: use Server header instead of OCCI-Server
    response["OCCI-Server"] = "OCCI/1.2"
    response["Accept"] = "application/json"
    return response


def validate_request(request, authentication_required=True,
                     has_data=False, **kwargs):
    """ This function checks if the request's content type is
        application/json and if the data is a valid json object. If the
        authentication_required parameter is 'True', it will also check if
        the user is authenticated. """
    # checking if the user is authenticated
    if authentication_required:
        if not request.user.is_authenticated():
            raise OcciRequestNotValid("Authentication required.", status=403)
    if has_data:
        # checking content type
        if request.META.get("CONTENT_TYPE") != "application/json":
            raise OcciRequestNotValid("Only application/json content type" +
                                      " is allowed.")
        # checking if the data is a valid json
        try:
            data = json.loads(request.body.decode("utf-8"))
        except KeyError:
            raise OcciRequestNotValid("The json provided in the request is " +
                                      "not valid.")
        # checking if provided keys are in the json
        if "data_keys" in kwargs:
            for key in kwargs["data_keys"]:
                if key not in data:
                    raise OcciRequestNotValid(key + " key is required.")
        # if validation was successful, the function returns the parsed
        # json data
        return data


def set_optional_attributes(self, optional_attributes, kwargs):
    """ Sets the optional arguments of an instance.
        If the kwargs dictionary has any values with the keys defined in
        the optional_attributes tuple, it sets them on the instance """
    for k, v in kwargs.iteritems():
        if k in optional_attributes:
            setattr(self, k, v)


def action_list_for_resource(actions):
    """ Creates a list of actions for Resource object rendering """
    acts = []
    for action in actions:
        acts.append(action.scheme + action.term)
    return acts
