from django.core.exceptions import ValidationError
from django.forms import fields
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.ipv6 import is_valid_ipv6_address
from south.modelsinspector import add_introspection_rules
import re

mac_re = re.compile(r'^([0-9a-fA-F]{2}([:-]?|$)){6}$')
alfanum_re = re.compile(r'^[A-Za-z0-9_-]+$')
domain_re = re.compile(r'^([A-Za-z0-9_-]\.?)+$')
wildcard_domain_re = re.compile(r'^(\*\.)?([A-Za-z0-9_-]\.?)+$')
ipv4_re = re.compile('^[0-9]+\.([0-9]+)\.([0-9]+)\.([0-9]+)$')
reverse_domain_re = re.compile(r'^(%\([abcd]\)d|[a-z0-9.-])+$')

class MACAddressFormField(fields.RegexField):
    default_error_messages = {
        'invalid': _(u'Enter a valid MAC address.'),
    }

    def __init__(self, *args, **kwargs):
        super(MACAddressFormField, self).__init__(mac_re, *args, **kwargs)

class MACAddressField(models.Field):
    empty_strings_allowed = False
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 17
        super(MACAddressField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return 'CharField'

    def formfield(self, **kwargs):
        defaults = {'form_class': MACAddressFormField}
        defaults.update(kwargs)
        return super(MACAddressField, self).formfield(**defaults)
add_introspection_rules([], ["firewall\.fields\.MACAddressField"])

def val_alfanum(value):
    """Validate whether the parameter is a valid alphanumeric value."""
    if not alfanum_re.match(value):
        raise ValidationError(_(u'%s - only letters, numbers, underscores '
            'and hyphens are allowed!') % value)

def is_valid_domain(value):
    """Check whether the parameter is a valid domain name."""
    return domain_re.match(value) is not None

def val_domain(value):
    """Validate whether the parameter is a valid domin name."""
    if not is_valid_domain(value):
        raise ValidationError(_(u'%s - invalid domain name') % value)

def val_wildcard_domain(value):
    """Validate whether the parameter is a valid domin name."""
    if not wildcard_domain_re.match(value):
        raise ValidationError(_(u'%s - invalid domain name') % value)

def is_valid_reverse_domain(value):
    """Check whether the parameter is a valid reverse domain name."""
    return reverse_domain_re.match(value) is not None

def val_reverse_domain(value):
    """Validate whether the parameter is a valid reverse domain name."""
    if not is_valid_reverse_domain(value):
        raise ValidationError(u'%s - invalid reverse domain name' % value)

def is_valid_ipv4_address(value):
    """Check whether the parameter is a valid IPv4 address."""
    return ipv4_re.match(value) is not None

def val_ipv4(value):
    """Validate whether the parameter is a valid IPv4 address."""
    if not is_valid_ipv4_address(value):
        raise ValidationError(_(u'%s - not an IPv4 address') % value)

def val_ipv6(value):
    """Validate whether the parameter is a valid IPv6 address."""
    if not is_valid_ipv6_address(value):
        raise ValidationError(_(u'%s - not an IPv6 address') % value)

def ipv4_2_ipv6(ipv4):
    """Convert IPv4 address string to IPv6 address string."""
    val_ipv4(ipv4)
    m = ipv4_re.match(ipv4)
    return ("2001:738:2001:4031:%s:%s:%s:0" %
        (m.group(1), m.group(2), m.group(3)))
