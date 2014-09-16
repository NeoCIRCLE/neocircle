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
