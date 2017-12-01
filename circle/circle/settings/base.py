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

"""Common settings and globals."""
# flake8: noqa
from os import environ
from os.path import abspath, basename, join, normpath, isfile, expanduser
from sys import path
from subprocess import check_output
from uuid import getnode

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _
from json import loads

from util import get_env_variable
from static_and_pipeline import *


# Normally you should not import ANYTHING from Django directly
# into your settings, but ImproperlyConfigured is an exception.


# Site name:
SITE_NAME = basename(BASE_DIR)

# Url to site: (e.g. http://localhost:8080/)
DJANGO_URL = get_env_variable('DJANGO_URL', '/')

# Add our project to our pythonpath, this way we don't need to type our project
# name in our dotted import paths:
path.append(BASE_DIR)
########## END PATH CONFIGURATION


########## DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = False

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
TEMPLATE_DEBUG = DEBUG
########## END DEBUG CONFIGURATION


########## MANAGER CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = (
    ('Root', 'root@localhost'),
)

EMAIL_SUBJECT_PREFIX = get_env_variable('DJANGO_SUBJECT_PREFIX', '[CIRCLE] ')

########## END MANAGER CONFIGURATION


########## DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.' +
        get_env_variable('DJANG_DB_TYPE', 'postgresql_psycopg2'),
        'NAME':  get_env_variable('DJANGO_DB_NAME', 'circle'),
        'USER':  get_env_variable('DJANGO_DB_USER', 'circle'),
        'PASSWORD':  get_env_variable('DJANGO_DB_PASSWORD'),
        'HOST': get_env_variable('DJANGO_DB_HOST', ''),
        'PORT': get_env_variable('DJANGO_DB_PORT', ''),
    }
}
########## END DATABASE CONFIGURATION


########## GENERAL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#time-zone
try:
    with open("/etc/timezone", "r") as f:
        systz = f.readline().rstrip()
except:
    systz = None

TIME_ZONE = get_env_variable('DJANGO_TIME_ZONE', default=systz)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = get_env_variable("DJANGO_LANGUAGE_CODE", "en")

# https://docs.djangoproject.com/en/dev/ref/settings/#languages
LANGUAGES = (
    ('en', _('English')),
    ('hu', _('Hungarian')),
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True
########## END GENERAL CONFIGURATION


########## SECRET CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Note: This key should only be used for development and testing.
SECRET_KEY = r"a5w*b0wajigd^kd7b=@w=5=+l_0c62@vljnhzqu3dfc@vx2jw-"
########## END SECRET CONFIGURATION


########## SITE CONFIGURATION
# Hosts/domain names that are valid for this site
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []
########## END SITE CONFIGURATION


########## FIXTURE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-FIXTURE_DIRS
FIXTURE_DIRS = (
    normpath(join(SITE_ROOT, 'fixtures')),
)
########## END FIXTURE CONFIGURATION


########## TEMPLATE CONFIGURATION

# See: https://docs.djangoproject.com/en/dev/ref/settings/#TEMPLATES
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS' : (
        normpath(join(SITE_ROOT, '../../site-circle/templates')),
        normpath(join(SITE_ROOT, 'templates')),
    ),
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': (
            'django.contrib.auth.context_processors.auth',
            'django.template.context_processors.debug',
            'django.template.context_processors.i18n',
            'django.template.context_processors.media',
            'django.template.context_processors.static',
            'django.template.context_processors.tz',
            'django.contrib.messages.context_processors.messages',
            'django.template.context_processors.request',
            'dashboard.context_processors.notifications',
            'dashboard.context_processors.extract_settings',
            'dashboard.context_processors.broadcast_messages',
        ),
    },
}]
########## END TEMPLATE CONFIGURATION


########## MIDDLEWARE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#middleware-classes
MIDDLEWARE_CLASSES = (
    # Default Django middleware.
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)
########## END MIDDLEWARE CONFIGURATION


########## URL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = '%s.urls' % SITE_NAME
########## END URL CONFIGURATION


########## APP CONFIGURATION
DJANGO_APPS = (
    # Default Django apps:
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Useful template tags:
    # 'django.contrib.humanize',

    # Django autocomplete light
    # it needs registering before django admin
    'dal',
    'dal_select2',
    # Admin panel and documentation:
    'django.contrib.admin',
    # 'django.contrib.admindocs',
)

THIRD_PARTY_APPS = (
    'django_tables2',
    'crispy_forms',
    'sizefield',
    'taggit',
    'statici18n',
    'django_sshkey',
    'pipeline',
)


# Apps specific for this project go here.
LOCAL_APPS = (
    'common',
    'vm',
    'storage',
    'firewall',
    'network',
    'dashboard',
    'manager',
    'acl',
    'monitor',
    'request',
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS
########## END APP CONFIGURATION


########## LOGGING CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#logging
# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(asctime)s [%(levelname)s]: %(name)s %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'syslog': {
            'level': 'INFO',
            'class': 'logging.handlers.SysLogHandler',
            'formatter': 'simple',
            'address': '/dev/log',
            # 'socktype': SOCK_STREAM,
            # 'address': ('host', '514'),
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins', 'syslog'],
            'level': 'INFO',
            'propagate': True,
        },
    }
}
########## END LOGGING CONFIGURATION


########## WSGI CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = '%s.wsgi.application' % SITE_NAME
########## END WSGI CONFIGURATION

FIREWALL_SETTINGS = loads(get_env_variable('DJANGO_FIREWALL_SETTINGS'))

CRISPY_TEMPLATE_PACK = 'bootstrap3'

# format: id: (name, port, protocol)
VM_ACCESS_PROTOCOLS = loads(get_env_variable('DJANGO_VM_ACCESS_PROTOCOLS',
                                             '''{"nx": ["NX", 22, "tcp"],
                                                 "rdp": ["RDP", 3389, "tcp"],
                                                 "ssh": ["SSH", 22, "tcp"]}'''))
VM_SCHEDULER = 'manager.scheduler'

#BROKER_URL = get_env_variable('AMQP_URI')

#BROKER_URL=get_env_variable('AMQP_URI')

CACHES = {
    'default': {
        'BACKEND': 'pylibmc',
        'LOCATION': '127.0.0.1:11211',
    }
}


if get_env_variable('DJANGO_SAML', 'FALSE') == 'TRUE':
    try:
        from shutil import which  # python >3.4
    except ImportError:
        from shutilwhich import which
    from saml2 import BINDING_HTTP_POST, BINDING_HTTP_REDIRECT

    INSTALLED_APPS += (
        'djangosaml2',
    )
    AUTHENTICATION_BACKENDS = (
        'django.contrib.auth.backends.ModelBackend',
        'common.backends.Saml2Backend',
    )

    remote_metadata = join(SITE_ROOT, 'remote_metadata.xml')
    if not isfile(remote_metadata):
        raise ImproperlyConfigured('Download SAML2 metadata to %s' %
                                   remote_metadata)
    required_attrs = loads(get_env_variable('DJANGO_SAML_REQUIRED',
                                            '["uid"]'))
    optional_attrs = loads(get_env_variable('DJANGO_SAML_OPTIONAL',
                                            '["mail", "cn", "sn"]'))

    SAML_CONFIG = {
        'xmlsec_binary': which('xmlsec1'),
        'entityid': DJANGO_URL + 'saml2/metadata/',
        'attribute_map_dir': join(SITE_ROOT, 'attribute-maps'),
        'service': {
            'sp': {
                'name': SITE_NAME,
                'endpoints': {
                    'assertion_consumer_service': [
                        (DJANGO_URL + 'saml2/acs/', BINDING_HTTP_POST),
                    ],
                    'single_logout_service': [
                        (DJANGO_URL + 'saml2/ls/', BINDING_HTTP_REDIRECT),
                    ],
                },
                'required_attributes': required_attrs,
                'optional_attributes': optional_attrs,
            },
        },
        'metadata': {'local': [remote_metadata], },
        'key_file': join(SITE_ROOT, 'samlcert.key'),  # private part
        'cert_file': join(SITE_ROOT, 'samlcert.pem'),  # public part
        'encryption_keypairs': [{
            'key_file': join(SITE_ROOT, 'samlcert.key'),  # private part
            'cert_file': join(SITE_ROOT, 'samlcert.pem'),  # public part
        }]
    }
    try:
        SAML_CONFIG += loads(get_env_variable('DJANGO_SAML_SETTINGS'))
    except ImproperlyConfigured:
        pass
    SAML_CREATE_UNKNOWN_USER = True
    SAML_ATTRIBUTE_MAPPING = loads(get_env_variable(
        'DJANGO_SAML_ATTRIBUTE_MAPPING',
        '{"mail": ["email"], "sn": ["last_name"], '
        '"uid": ["username"], "cn": ["first_name"]}'))
    SAML_GROUP_ATTRIBUTES = get_env_variable(
        'DJANGO_SAML_GROUP_ATTRIBUTES', '').split(',')
    SAML_GROUP_OWNER_ATTRIBUTES = get_env_variable(
        'DJANGO_SAML_GROUP_OWNER_ATTRIBUTES', '').split(',')

    SAML_CREATE_UNKNOWN_USER = True
    if get_env_variable('DJANGO_SAML_ORG_ID_ATTRIBUTE', False) is not False:
        SAML_ORG_ID_ATTRIBUTE = get_env_variable(
            'DJANGO_SAML_ORG_ID_ATTRIBUTE')
    SAML_MAIN_ATTRIBUTE_MAX_LENGTH = int(get_env_variable(
        "DJANGO_SAML_MAIN_ATTRIBUTE_MAX_LENGTH", 0))

LOGIN_REDIRECT_URL = "/"

AGENT_DIR = get_env_variable(
    'DJANGO_AGENT_DIR', join(unicode(expanduser("~")), 'agent'))
    # AGENT_DIR is the root directory for the agent.
    # The directory structure SHOULD be:
    # /home/username/agent
    # |-- agent-linux
    # |    |-- .git
    # |    +-- ...
    # |-- agent-win
    # |    +-- agent-win-%(version).exe
    #

try:
    git_env = {'GIT_DIR': join(join(AGENT_DIR, "agent-linux"), '.git')}
    AGENT_VERSION = check_output(
        ('git', 'log', '-1', r'--pretty=format:%h', 'HEAD'), env=git_env)
except:
    AGENT_VERSION = None

LOCALE_PATHS = (join(SITE_ROOT, 'locale'), )
COMPANY_NAME = get_env_variable("COMPANY_NAME", "BME IK 2015")

first, last = get_env_variable(
    'VNC_PORT_RANGE', '50000, 60000').replace(' ', '').split(',')
VNC_PORT_RANGE = (int(first), int(last))  # inclusive start, exclusive end

graphite_host = environ.get("GRAPHITE_HOST", None)
graphite_port = environ.get("GRAPHITE_PORT", None)
if graphite_host and graphite_port:
    GRAPHITE_URL = 'http://%s:%s/render/' % (graphite_host, graphite_port)
else:
    GRAPHITE_URL = None

STORE_BASIC_AUTH = get_env_variable("STORE_BASIC_AUTH", "") == "True"
STORE_VERIFY_SSL = get_env_variable("STORE_VERIFY_SSL", "") == "True"
STORE_SSL_AUTH = get_env_variable("STORE_SSL_AUTH", "") == "True"
STORE_CLIENT_USER = get_env_variable("STORE_CLIENT_USER", "")
STORE_CLIENT_PASSWORD = get_env_variable("STORE_CLIENT_PASSWORD", "")
STORE_CLIENT_KEY = get_env_variable("STORE_CLIENT_KEY", "")
STORE_CLIENT_CERT = get_env_variable("STORE_CLIENT_CERT", "")
STORE_URL = get_env_variable("STORE_URL", "")

SESSION_COOKIE_NAME = "csessid%x" % (((getnode() // 139) ^
                                      (getnode() % 983)) & 0xffff)

MAX_NODE_RAM = get_env_variable("MAX_NODE_RAM", 1024)

# Url to download the client: (e.g. http://circlecloud.org/client/download/)
CLIENT_DOWNLOAD_URL = get_env_variable('CLIENT_DOWNLOAD_URL', 'http://circlecloud.org/client/download/')

ADMIN_ENABLED = False

BLACKLIST_PASSWORD = get_env_variable("BLACKLIST_PASSWORD", "")
BLACKLIST_HOOK_URL = get_env_variable("BLACKLIST_HOOK_URL", "")
REQUEST_HOOK_URL = get_env_variable("REQUEST_HOOK_URL", "")

SSHKEY_EMAIL_ADD_KEY = False

TWO_FACTOR_ISSUER = get_env_variable("TWO_FACTOR_ISSUER", "CIRCLE")

DEFAULT_USERNET_VLAN_NAME = (
    get_env_variable("DEFAULT_USERNET_VLAN_NAME", "usernet"))
USERNET_MAX = 2 ** 12
