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

from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login


class OcciAuthForm(AuthenticationForm):
    """ An authentication form for the OCCI implementation. """

    def __init__(self, request, *args, **kwargs):
        super(OcciAuthForm, self).__init__(*args, **kwargs)
        self.request = request

    def confirm_login_allowed(self, user):
        super(OcciAuthForm, self).confirm_login_allowed(user)
        login(self.request, user)
