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

"""Production settings and globals."""
# flake8: noqa


from os import environ

from base import *  # noqa


def get_env_setting(setting):
    """ Get the environment setting or return exception """
    try:
        return environ[setting]
    except KeyError:
        error_msg = "Set the %s env variable" % setting
        raise ImproperlyConfigured(error_msg)

########## HOST CONFIGURATION
# See: https://docs.djangoproject.com/en/1.5/releases/1.5/
#      #allowed-hosts-required-in-production
ALLOWED_HOSTS = get_env_setting('DJANGO_ALLOWED_HOSTS').split(',')
########## END HOST CONFIGURATION

########## EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

try:
    # See: https://docs.djangoproject.com/en/dev/ref/settings/#email-host
    EMAIL_HOST = environ.get('EMAIL_HOST')
except ImproperlyConfigured:
    pass
else:
    # https://docs.djangoproject.com/en/dev/ref/settings/#email-host-password
    EMAIL_HOST_PASSWORD = environ.get('EMAIL_HOST_PASSWORD', '')

    # See: https://docs.djangoproject.com/en/dev/ref/settings/#email-host-user
    EMAIL_HOST_USER = environ.get('EMAIL_HOST_USER', 'your_email@example.com')

    # See: https://docs.djangoproject.com/en/dev/ref/settings/#email-port
    EMAIL_PORT = environ.get('EMAIL_PORT', 587)

    # See: https://docs.djangoproject.com/en/dev/ref/settings/#email-use-tls
    EMAIL_USE_TLS = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
EMAIL_SUBJECT_PREFIX = '[%s] ' % SITE_NAME

# See: https://docs.djangoproject.com/en/dev/ref/settings/#server-email
SERVER_EMAIL = EMAIL_HOST_USER
########## END EMAIL CONFIGURATION


########## CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
try:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
            'LOCATION': get_env_variable('DJANGO_MEMCACHED'),
        }
    }
except ImproperlyConfigured:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': SITE_NAME,
        }
    }
########## END CACHE CONFIGURATION


########## SECRET CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = get_env_setting('SECRET_KEY')
########## END SECRET CONFIGURATION
