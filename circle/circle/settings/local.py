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

"""Development settings and globals."""


from base import *  # noqa


########## DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
TEMPLATE_DEBUG = DEBUG
########## END DEBUG CONFIGURATION


########## EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
########## END EMAIL CONFIGURATION


########## DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': normpath(join(DJANGO_ROOT, 'default.db')),
#         'USER': '',
#         'PASSWORD': '',
#         'HOST': '',
#         'PORT': '',
#     }
# }
########## END DATABASE CONFIGURATION


########## CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
        'LOCATION': '127.0.0.1:11211',
    }
}
########## END CACHE CONFIGURATION


########## TOOLBAR CONFIGURATION
# https://github.com/django-debug-toolbar/django-debug-toolbar#installation
if get_env_variable('DJANGO_TOOLBAR', 'FALSE') == 'TRUE':
    INSTALLED_APPS += (
        'debug_toolbar',
    )

    # https://github.com/django-debug-toolbar/django-debug-toolbar#installation
    INTERNAL_IPS = (
        get_env_variable('SSH_CLIENT', '127.0.0.1').split(' ')[0],
    )

    # https://github.com/django-debug-toolbar/django-debug-toolbar#installation
    MIDDLEWARE_CLASSES += (
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    )

    # https://github.com/django-debug-toolbar/django-debug-toolbar#installation
    DEBUG_TOOLBAR_CONFIG = {
        'INTERCEPT_REDIRECTS': False,
        'SHOW_TEMPLATE_CONTEXT': True,
    }
    ########## END TOOLBAR CONFIGURATION

LOGGING['loggers']['djangosaml2'] = {'handlers': ['console'], 'level': 'DEBUG'}

LOGGING['handlers']['console'] = {'level': 'DEBUG',
                                  'class': 'logging.StreamHandler',
                                  'formatter': 'simple'}
for i in LOCAL_APPS:
    LOGGING['loggers'][i] = {'handlers': ['console'], 'level': 'DEBUG'}

CRISPY_FAIL_SILENTLY = not DEBUG

# propagate exceptions from signals
if DEBUG:
    from django.dispatch import Signal
    Signal.send_robust = Signal.send
