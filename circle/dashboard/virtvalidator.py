from django.core.exceptions import ValidationError
from lxml import etree as ET


rng_file = "/usr/share/libvirt/schemas/domain.rng"

header = """<domain type='kvm'>
  <name>validator</name>
  <memory unit='KiB'>1024</memory>
  <os>
    <type>hvm</type>
  </os>"""
footer = """</domain>"""


def domain_validator(value):
    xml = header + value + footer
    relaxng = ET.RelaxNG(file=rng_file)
    if not relaxng.validate(ET.fromstring(xml)):
        raise ValidationError("%s is not valid libvirt Domain xml." % value)
