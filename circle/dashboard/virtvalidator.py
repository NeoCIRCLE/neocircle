from django.core.exceptions import ValidationError
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
