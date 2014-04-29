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
)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache'
    }
}

LOGGING['loggers']['djangosaml2'] = {'handlers': ['console'],
                                     'level': 'CRITICAL'}

LOGGING['handlers']['console'] = {'level': 'WARNING',
                                  'class': 'logging.StreamHandler',
                                  'formatter': 'simple'}
for i in LOCAL_APPS:
    LOGGING['loggers'][i] = {'handlers': ['console'], 'level': 'CRITICAL'}
