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

import os

from .base import *  # flake8:noqa


# fix https://github.com/django-nose/django-nose/issues/197
# AttributeError: 'module' object has no attribute 'commit_unless_managed'
# TypeError: _skip_create_test_db() got an unexpected keyword argument 'keepdb'

from django.db import transaction
from django_nose import runner


def _skip_create_test_db(self, verbosity=1, autoclobber=False, serialize=True,
                         keepdb=True):
    return old_skip_create_test_db(
        self, verbosity=verbosity, autoclobber=autoclobber,
        serialize=serialize)


setattr(transaction, "commit_unless_managed", lambda using: using)
old_skip_create_test_db = runner._skip_create_test_db
setattr(runner, "_skip_create_test_db", _skip_create_test_db)


os.environ['REUSE_DB'] = "1"
os.environ['DJANGO_TEST_DB_NAME'] = "circle"
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.' +
        get_env_variable('DJANG_DB_TYPE', 'postgresql_psycopg2'),
        'NAME':  get_env_variable('DJANGO_DB_NAME', 'circle'),
        'TEST_NAME': get_env_variable('DJANGO_TEST_DB_NAME', 'circle'),
        'USER':  get_env_variable('DJANGO_DB_USER', 'circle'),
        'PASSWORD':  get_env_variable('DJANGO_DB_PASSWORD'),
        'HOST': get_env_variable('DJANGO_DB_HOST', ''),
        'PORT': get_env_variable('DJANGO_DB_PORT', ''),
    }
}
SOUTH_TESTS_MIGRATE = False

INSTALLED_APPS += (
    'acl.tests',
    'django_nose',
    'django_jenkins',
)
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'


path_to_selenium_test = os.path.join(SITE_ROOT, "dashboard/tests/selenium")
NOSE_ARGS = ['--stop', '--with-doctest', '--with-selenium-driver',
             '--selenium-driver=firefox', '-w%s' % path_to_selenium_test]

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
