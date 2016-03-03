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

from string import ascii_letters
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.ipv6 import is_valid_ipv6_address
from django import forms
from netaddr import (IPAddress, IPNetwork, AddrFormatError, ZEROFILL,
                     EUI, mac_unix, AddrConversionError)
import re


alfanum_re = re.compile(r'^[A-Za-z0-9_-]+$')
domain_re = re.compile(r'^([A-Za-z0-9_-]\.?)+$')
domain_wildcard_re = re.compile(r'^(\*\.)?([A-Za-z0-9_-]\.?)+$')
ipv4_re = re.compile('^([0-9]+)\.([0-9]+)\.([0-9]+)\.([0-9]+)$')
reverse_domain_re = re.compile(r'^(%\([abcd]\)d|[a-z0-9.-])+$')


class mac_custom(mac_unix):
    word_fmt = '%.2X'


class MACAddressFormField(forms.Field):
    default_error_messages = {
        'invalid': _(u'Enter a valid MAC address. %s'),
    }

    def validate(self, value):
        try:
            return MACAddressField.to_python.im_func(None, value)
        except (AddrFormatError, TypeError, ValidationError) as e:
            raise ValidationError(self.default_error_messages['invalid']
                                  % unicode(e))


class MACAddressField(models.Field):
    description = _('MAC Address object')
    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 17
        super(MACAddressField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if not value:
            return None

        if isinstance(value, EUI):
            return value

        return EUI(value, dialect=mac_custom)

    def get_internal_type(self):
        return 'CharField'

    def get_prep_value(self, value, prepared=False):
        if not value:
            return None

        if isinstance(value, EUI):
            return str(value)

        return value

    def formfield(self, **kwargs):
        defaults = {'form_class': MACAddressFormField}
        defaults.update(kwargs)
        return super(MACAddressField, self).formfield(**defaults)


class IPAddressFormField(forms.Field):
    default_error_messages = {
        'invalid': _(u'Enter a valid IP address. %s'),
    }

    def validate(self, value):
        try:
            IPAddressField(version=self.version).to_python(value)
        except (AddrFormatError, TypeError, ValueError) as e:
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

    def get_internal_type(self):
        return "CharField"

    def to_python(self, value):
        if not value:
            return None

        if isinstance(value, IPAddress):
            return value

        return IPAddress(value.split('/')[0], version=self.version,
                         flags=ZEROFILL)

    def get_prep_value(self, value, prepared=False):
        if not value:
            return None

        if isinstance(value, IPAddress):
            if self.version == 4:
                return '.'.join("%03d" % x for x in value.words)
            else:
                return ':'.join("%04X" % x for x in value.words)
        return value

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
            return IPNetworkField(version=self.version).to_python(value)
        except (AddrFormatError, TypeError) as e:
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

    def to_python(self, value):
        if not value:
            return None

        if isinstance(value, IPNetwork):
            return value

        return IPNetwork(value, version=self.version)

    def get_internal_type(self):
        return "CharField"

    def get_prep_value(self, value, prepared=False):
        if not value:
            return None

        if isinstance(value, IPNetwork):
            if self.version == 4:
                return ('.'.join("%03d" % x for x in value.ip.words) +
                        '/%02d' % value.prefixlen)
            else:
                return (':'.join("%04X" % x for x in value.ip.words) +
                        '/%03d' % value.prefixlen)
        return value

    def formfield(self, **kwargs):
        defaults = {'form_class': IPNetworkFormField}
        defaults['version'] = self.version
        defaults.update(kwargs)
        return super(IPNetworkField, self).formfield(**defaults)


def val_alfanum(value):
    """Validate whether the parameter is a valid alphanumeric value."""
    if not alfanum_re.match(value):
        raise ValidationError(_(u'%s - only letters, numbers, underscores '
                                'and hyphens are allowed!') % value)


def is_valid_domain(value):
    """Check whether the parameter is a valid domain name."""
    return domain_re.match(value) is not None


def is_valid_domain_wildcard(value):
    """Check whether the parameter is a valid domain name."""
    return domain_wildcard_re.match(value) is not None


def val_domain(value):
    """Validate whether the parameter is a valid domin name."""
    if not is_valid_domain(value):
        raise ValidationError(_(u'%s - invalid domain name') % value)


def val_domain_wildcard(value):
    """Validate whether the parameter is a valid domin name."""
    if not is_valid_domain_wildcard(value):
        raise ValidationError(_(u'%s - invalid domain name') % value)


def is_valid_reverse_domain(value):
    """Check whether the parameter is a valid reverse domain name."""
    return reverse_domain_re.match(value) is not None


def val_reverse_domain(value):
    """Validate whether the parameter is a valid reverse domain name."""
    if not is_valid_reverse_domain(value):
        raise ValidationError(u'%s - invalid reverse domain name' % value)


def val_ipv6_template(value):
    """Validate whether the parameter is a valid ipv6 template.

    Normal use:
    >>> val_ipv6_template("123::%(a)d:%(b)d:%(c)d:%(d)d")
    >>> val_ipv6_template("::%(a)x:%(b)x:%(c)d:%(d)d")

    Don't have to use all bytes from the left (no a):
    >>> val_ipv6_template("::%(b)x:%(c)d:%(d)d")

    But have to use all ones to the right (a, but no b):
    >>> val_ipv6_template("::%(a)x:%(c)d:%(d)d")
    Traceback (most recent call last):
        ...
    ValidationError: [u"template doesn't use parameter b"]

    Detects valid templates building invalid ips:
    >>> val_ipv6_template("xxx::%(a)d:%(b)d:%(c)d:%(d)d")
    Traceback (most recent call last):
        ...
    ValidationError: [u'template renders invalid IPv6 address']

    Also IPv4-compatible addresses are invalid:
    >>> val_ipv6_template("::%(a)02x%(b)02x:%(c)d:%(d)d")
    Traceback (most recent call last):
        ...
    ValidationError: [u'template results in IPv4 address']
    """
    tpl = {ascii_letters[i]: 255 for i in range(4)}
    try:
        v6 = value % tpl
    except:
        raise ValidationError(_('%s: invalid template') % value)

    used = False
    for i in ascii_letters[:4]:
        try:
            value % {k: tpl[k] for k in tpl if k != i}
        except KeyError:
            used = True  # ok, it misses this key
        else:
            if used:
                raise ValidationError(
                    _("template doesn't use parameter %s") % i)
    try:
        v6 = IPAddress(v6, 6)
    except:
        raise ValidationError(_('template renders invalid IPv6 address'))
    try:
        v6.ipv4()
    except (AddrConversionError, AddrFormatError):
        pass  # can't converted to ipv4 == it's real ipv6
    else:
        raise ValidationError(_('template results in IPv4 address'))


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
