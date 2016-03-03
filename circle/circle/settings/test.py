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

from .base import *  # noqa

# flake8: noqa

########## IN-MEMORY TEST DATABASE
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "USER": "",
        "PASSWORD": "",
        "HOST": "",
        "PORT": "",
    },
}
SOUTH_TESTS_MIGRATE = False


INSTALLED_APPS += (
    'acl.tests',
    'django_nose',
)
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
NOSE_ARGS = ['--with-doctest', '--exclude-dir=dashboard/tests/selenium']
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache'
    }
}

LOGGING['loggers']['djangosaml2'] = {'handlers': ['console'],
                                     'level': 'CRITICAL'}

level = environ.get('LOGLEVEL', 'CRITICAL')
LOGGING['handlers']['console'] = {'level': level,
                                  'class': 'logging.StreamHandler',
                                  'formatter': 'simple'}
for i in LOCAL_APPS:
    LOGGING['loggers'][i] = {'handlers': ['console'], 'level': level}

# don't print SQL queries
LOGGING['handlers']['null'] = {'level': "DEBUG",
                               'class': "django.utils.log.NullHandler"}
LOGGING['loggers']['django.db.backends'] = {
    'handlers': ['null'],
    'propagate': False,
    'level': 'DEBUG',
}

# Forbid store usage
STORE_URL = ""

# buildbot doesn't love pipeline
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

SAML_MAIN_ATTRIBUTE_MAX_LENGTH=0  # doctest on SAML2 backend runs either way
