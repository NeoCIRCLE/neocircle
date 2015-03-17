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

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from lxml import etree as ET
import logging

rng_file = "/usr/share/libvirt/schemas/domain.rng"

# Mandatory xml elements dor parsing
header = "<domain type='kvm'><name>validator</name>\
<memory unit='KiB'>1024</memory>\
<os><type>hvm</type></os>"
footer = "</domain>"

logger = logging.getLogger()


def domain_validator(value):
    xml = header + value + footer
    try:
        parsed_xml = ET.fromstring(xml)
    except Exception as e:
        raise ValidationError(e.message)
    try:
        relaxng = ET.RelaxNG(file=rng_file)
    except:
        logger.critical("%s RelaxNG libvirt domain schema file "
                        "is missing for validation.", rng_file)
    else:
        try:
            relaxng.assertValid(parsed_xml)
        except Exception as e:
            raise ValidationError(e.message)


def connect_command_template_validator(value):
    """Validate value as a connect command template.

    >>> try: connect_command_template_validator("%(host)s")
    ... except ValidationError as e: print e
    ...
    >>> connect_command_template_validator("%(host)s")
    >>> try: connect_command_template_validator("%(host)s %s")
    ... except ValidationError as e: print e
    ...
    [u'Invalid template string.']
    """

    try:
        value % {
            'username': "uname",
            'password': "pw",
            'host': "111.111.111.111",
            'port': 12345,
        }
    except (KeyError, TypeError, ValueError):
        raise ValidationError(_("Invalid template string."))
