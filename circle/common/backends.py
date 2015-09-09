# -*- coding: utf-8 -*-
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

import re
import logging
import sha

from django.conf import settings
from djangosaml2.backends import Saml2Backend as Saml2BackendBase

logger = logging.getLogger(__name__)


class Saml2Backend(Saml2BackendBase):
    u"""
    >>> b = Saml2Backend()
    >>> b.clean_user_main_attribute(u'Ékezetes Enikő')
    u'+00c9kezetes+0020Enik+0151'
    >>> b.clean_user_main_attribute(u'Cé++')
    u'C+00e9+002b+002b'
    >>> b.clean_user_main_attribute(u'test')
    u'test'
    >>> b.clean_user_main_attribute(u'3+4')
    u'3+002b4'
    """
    def clean_user_main_attribute(self, main_attribute):
        def replace(match):
            match = match.group()
            return '+%04x' % ord(match)

        if isinstance(main_attribute, str):
            main_attribute = main_attribute.decode('UTF-8')
        assert isinstance(main_attribute, unicode)
        attr = re.sub(r'[^\w.@-]', replace, main_attribute)
        max_length = settings.SAML_MAIN_ATTRIBUTE_MAX_LENGTH
        if max_length > 0 and len(attr) > max_length:
            logger.info("Main attribute '%s' is too long." % attr)
            hashed = sha.new(attr).hexdigest()
            attr = hashed[:max_length]
            logger.info("New main attribute: %s" % attr)
        return attr

    def _set_attribute(self, obj, attr, value):
        if attr == 'username':
            value = self.clean_user_main_attribute(value)
        return super(Saml2Backend, self)._set_attribute(obj, attr, value)
