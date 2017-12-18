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
from sys import argv

from base import *  # noqa

if 'runserver' in argv:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')

########## HOST CONFIGURATION
# See: https://docs.djangoproject.com/en/1.5/releases/1.5/
#      #allowed-hosts-required-in-production
ALLOWED_HOSTS = get_env_variable('DJANGO_ALLOWED_HOSTS').split(',')
########## END HOST CONFIGURATION

########## EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

try:
    # See: https://docs.djangoproject.com/en/dev/ref/settings/#email-host
    EMAIL_HOST = get_env_variable('EMAIL_HOST')
except ImproperlyConfigured:
    EMAIL_HOST = 'localhost'
else:
    # https://docs.djangoproject.com/en/dev/ref/settings/#email-host-password
    EMAIL_HOST_PASSWORD = get_env_variable('EMAIL_HOST_PASSWORD', '')

    # See: https://docs.djangoproject.com/en/dev/ref/settings/#email-host-user
    EMAIL_HOST_USER = get_env_variable('EMAIL_HOST_USER', 'your_email@example.com')

    # See: https://docs.djangoproject.com/en/dev/ref/settings/#email-port
    EMAIL_PORT = get_env_variable('EMAIL_PORT', 587)

    # See: https://docs.djangoproject.com/en/dev/ref/settings/#email-use-tls
    EMAIL_USE_TLS = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
EMAIL_SUBJECT_PREFIX = '[%s] ' % SITE_NAME

# See: https://docs.djangoproject.com/en/dev/ref/settings/#server-email
DEFAULT_FROM_EMAIL = get_env_variable('DEFAULT_FROM_EMAIL')
SERVER_EMAIL = get_env_variable('SERVER_EMAIL', DEFAULT_FROM_EMAIL)
########## END EMAIL CONFIGURATION


########## CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
from urlparse import urlsplit

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': urlsplit(get_env_variable('CACHE_URI')).netloc,
    }
}
########## END CACHE CONFIGURATION


########## SECRET CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = get_env_variable('SECRET_KEY')
########## END SECRET CONFIGURATION

level = environ.get('LOGLEVEL', 'INFO')
LOGGING['handlers']['syslog']['level'] = level
for i in LOCAL_APPS:
    LOGGING['loggers'][i] = {'handlers': ['syslog'], 'level': level}
LOGGING['loggers']['djangosaml2'] = {'handlers': ['syslog'], 'level': level}
LOGGING['loggers']['django'] = {'handlers': ['syslog'], 'level': level}


############ REST FRAMEWORK CONFIGURATION
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'common.pagination.RelativePageNumberPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAdminUser',
    ),
}
