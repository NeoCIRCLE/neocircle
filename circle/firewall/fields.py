from django.core.exceptions import ValidationError
from django.forms import fields
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.ipv6 import is_valid_ipv6_address
from south.modelsinspector import add_introspection_rules
from django import forms
from netaddr import IPAddress, IPNetwork, AddrFormatError, ZEROFILL
import re


mac_re = re.compile(r'^([0-9a-fA-F]{2}(:|$)){6}$')
alfanum_re = re.compile(r'^[A-Za-z0-9_-]+$')
domain_re = re.compile(r'^([A-Za-z0-9_-]\.?)+$')
ipv4_re = re.compile('^([0-9]+)\.([0-9]+)\.([0-9]+)\.([0-9]+)$')
reverse_domain_re = re.compile(r'^(%\([abcd]\)d|[a-z0-9.-])+$')
ipv6_template_re = re.compile(r'^(%\([abcd]\)[dxX]|[A-Za-z0-9:-])+$')


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

    def to_python(self, value):
        if not mac_re.search(str(value)):
            raise ValidationError(
                MACAddressFormField.default_error_messages['invalid'])
        return str(value)

    def formfield(self, **kwargs):
        defaults = {'form_class': MACAddressFormField}
        defaults.update(kwargs)
        return super(MACAddressField, self).formfield(**defaults)
add_introspection_rules([], ["firewall\.fields\.MACAddressField"])


class IPAddressFormField(forms.Field):
    default_error_messages = {
        'invalid': _(u'Enter a valid IP address. %s'),
    }

    def validate(self, value):
        try:
            return IPAddressField.from_str(value, version=self.version)
        except (AddrFormatError, TypeError), e:
            raise ValidationError(self.default_error_messages['invalid']
                                  % unicode(e))

    def __init__(self, *args, **kwargs):
        self.version = kwargs['version']
        del kwargs['version']
        super(IPAddressFormField, self).__init__(*args, **kwargs)


class IPAddressField(models.Field):
    description = _('IP Network object')
    __metaclass__ = models.SubfieldBase

    def __init__(self, version=4, serialize=True, *args, **kwargs):
        kwargs['max_length'] = 100
        self.version = version
        super(IPAddressField, self).__init__(*args, **kwargs)

    @staticmethod
    def from_str(value, version):
        if not value or value == "":
            return None

        if isinstance(value, IPAddress):
            return value

        return IPAddress(value.split('/')[0], version=version,
                         flags=ZEROFILL)

    def get_internal_type(self):
        return "CharField"

    def to_python(self, value):
        return IPAddressField.from_str(value, self.version)

    def get_db_prep_value(self, value, connection, prepared=False):
        if not value or value == "":
            return None

        if isinstance(value, IPAddress):
            if self.version == 4:
                return ('.'.join(["%03d" % x for x in value.words]))
            else:
                return (':'.join(["%04X" % x for x in value.words]))
        return value

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return str(self.get_prep_value(value))

    def clean(self, value, model_instance):
        value = super(IPAddressField, self).clean(value, model_instance)
        return self.get_prep_value(value)

    def formfield(self, **kwargs):
        defaults = {'form_class': IPAddressFormField}
        defaults['version'] = self.version
        defaults.update(kwargs)
        return super(IPAddressField, self).formfield(**defaults)


class IPNetworkFormField(forms.Field):
    default_error_messages = {
        'invalid': _(u'Enter a valid IP network. %s'),
    }

    def validate(self, value):
        try:
            return IPNetworkField.from_str(value, version=self.version)
        except (AddrFormatError, TypeError), e:
            raise ValidationError(self.default_error_messages['invalid']
                                  % unicode(e))

    def __init__(self, *args, **kwargs):
        self.version = kwargs['version']
        del kwargs['version']
        super(IPNetworkFormField, self).__init__(*args, **kwargs)


class IPNetworkField(models.Field):
    description = _('IP Network object')
    __metaclass__ = models.SubfieldBase

    def __init__(self, version=4, serialize=True, *args, **kwargs):
        kwargs['max_length'] = 100
        self.version = version
        super(IPNetworkField, self).__init__(*args, **kwargs)

    @staticmethod
    def from_str(value, version):
        if not value or value == "":
            return None

        if isinstance(value, IPNetwork):
            return value

        return IPNetwork(value, version=version)

    def get_internal_type(self):
        return "CharField"

    def to_python(self, value):
        return IPNetworkField.from_str(value, self.version)

    def get_db_prep_value(self, value, connection, prepared=False):
        if not value or value == "":
            return None

        if isinstance(value, IPNetwork):
            if self.version == 4:
                return ('.'.join(["%03d" % x for x in value.ip.words])
                        + '/%02d' % value.prefixlen)
            else:
                return (':'.join(["%04X" % x for x in value.ip.words])
                        + '/%03d' % value.prefixlen)
        return value

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return str(self.get_prep_value(value))

    def clean(self, value, model_instance):
        value = super(IPNetworkField, self).clean(value, model_instance)
        return self.get_prep_value(value)

    def formfield(self, **kwargs):
        defaults = {'form_class': IPNetworkFormField}
        defaults['version'] = self.version
        defaults.update(kwargs)
        return super(IPNetworkField, self).formfield(**defaults)

add_introspection_rules([], ["^firewall\.fields\.IP(Address|Network)Field"])


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


def is_valid_reverse_domain(value):
    """Check whether the parameter is a valid reverse domain name."""
    return reverse_domain_re.match(value) is not None


def val_reverse_domain(value):
    """Validate whether the parameter is a valid reverse domain name."""
    if not is_valid_reverse_domain(value):
        raise ValidationError(u'%s - invalid reverse domain name' % value)


def is_valid_ipv6_template(value):
    """Check whether the parameter is a valid ipv6 template."""
    return ipv6_template_re.match(value) is not None


def val_ipv6_template(value):
    """Validate whether the parameter is a valid ipv6 template."""
    if not is_valid_ipv6_template(value):
        raise ValidationError(u'%s - invalid reverse ipv6 template' % value)


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


def val_mx(value):
    """Validate whether the parameter is a valid MX address definition.

    Expected form is <priority>:<hostname>.
    """
    mx = value.split(':', 1)
    if not (len(mx) == 2 and mx[0].isdigit() and
            domain_re.match(mx[1])):
        raise ValidationError(_("Bad MX address format. "
                                "Should be: <priority>:<hostname>"))


def convert_ipv4_to_ipv6(ipv6_template, ipv4):
    """Convert IPv4 address string to IPv6 address string."""
    m = ipv4.words
    return IPAddress(ipv6_template % {'a': int(m[0]),
                                      'b': int(m[1]),
                                      'c': int(m[2]),
                                      'd': int(m[3])})
