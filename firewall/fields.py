from django.core.exceptions import ValidationError
from django.forms import fields
from django.db import models
from django.utils.translation import ugettext_lazy as _
from south.modelsinspector import add_introspection_rules
import re

mac_re = re.compile(r'^([0-9a-fA-F]{2}([:-]?|$)){6}$')
alfanum_re = re.compile(r'^[A-Za-z0-9_-]+$')
domain_re = re.compile(r'^([A-Za-z0-9_-]\.?)+$')
ipv4_re = re.compile('^[0-9]+\.([0-9]+)\.([0-9]+)\.([0-9]+)$')

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
        return "CharField"

    def formfield(self, **kwargs):
        defaults = {'form_class': MACAddressFormField}
        defaults.update(kwargs)
        return super(MACAddressField, self).formfield(**defaults)
add_introspection_rules([], ["firewall\.fields\.MACAddressField"])

def val_alfanum(value):
     if not alfanum_re.search(value):
          raise ValidationError(u'%s - csak betut, kotojelet, alahuzast, szamot tartalmazhat!' % value)

def val_domain(value):
     if not domain_re.search(value):
          raise ValidationError(u'%s - helytelen domain' % value)

def ipv4_2_ipv6(ipv4):
	m = ipv4_re.match(ipv4)
	return "2001:738:2001:4031:%s:%s:%s:0" % (m.group(1), m.group(2), m.group(3))
