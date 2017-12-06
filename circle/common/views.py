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

from django.shortcuts import render_to_response, redirect
from django.contrib import messages
from django.template import RequestContext
from django.http import JsonResponse
from django.utils.translation import ugettext_lazy as _

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


class CreateLimitedResourceMixin(object):
    resource_name = None
    model = None
    profile_attribute = None

    def post(self, *args, **kwargs):
        user = self.request.user
        try:
            limit = getattr(user.profile, self.profile_attribute)
        except Exception as e:
            logger.debug('No profile or %s: %s', self.profile_attribute, e)
        else:
            current = self.model.objects.filter(owner=user).count()
            logger.debug('%s current use: %d, limit: %d',
                         self.resource_name, current, limit)
            if current > limit:
                messages.error(self.request,
                               _('%s limit (%d) exceeded.')
                               % (self.resource_name, limit))
                if self.request.is_ajax():
                    return JsonResponse({'redirect': '/'})
                else:
                    return redirect('/')
        return super(CreateLimitedResourceMixin, self).post(*args, **kwargs)
