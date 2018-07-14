# Copyright 2014 Budapest University of Technology and Economics (BME IK)
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

from sys import exc_info

import logging

from django.shortcuts import render_to_response
from django.template import RequestContext

from .models import HumanReadableException

logger = logging.getLogger(__name__)


def get_context(request, exception):
    ctx = {}
    if issubclass(exception.__class__, HumanReadableException):
        try:
            if request.user.is_superuser:
                ctx['error'] = exception.get_admin_text()
            else:
                ctx['error'] = exception.get_user_text()
        except:
            pass
    return ctx


def handler500(request):
    cls, exception, traceback = exc_info()
    logger.exception("unhandled exception")
    ctx = get_context(request, exception)
    try:
        resp = render_to_response("500.html", ctx,
                                  RequestContext(request).flatten())
    except:
        resp = render_to_response("500.html", ctx)
    resp.status_code = 500
    return resp


def handler403(request):
    cls, exception, traceback = exc_info()
    ctx = get_context(request, exception)
    resp = render_to_response("403.html", ctx)
    resp.status_code = 403
    return resp
