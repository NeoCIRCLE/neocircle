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


from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from occi.utils import OcciRequestNotValid


class EnsureCsrfTokenMixin(object):

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, *args, **kwargs):
        return super(EnsureCsrfTokenMixin, self).dispatch(*args, **kwargs)


class OcciViewMixin(EnsureCsrfTokenMixin):

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated():
            return OcciRequestNotValid(message="Authentication required.",
                                       status=403).response
        return super(OcciViewMixin, self).dispatch(request, *args, **kwargs)
