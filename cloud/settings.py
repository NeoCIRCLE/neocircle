# Django settings for cloud project.


DEBUG = True
TEMPLATE_DEBUG = DEBUG
STAT_DEBUG = True

ADMINS = (
    ('IK', 'cloud@cloud.ik.bme.hu'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2',
                                              # 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'webadmin',                   # Or path to database file if
                                              # using sqlite3.
        'USER': 'webadmin',                   # Not used with sqlite3.
        'PASSWORD': 'asjklddfjklqjf',         # Not used with sqlite3.
        'HOST': '',                           # Set to empty string for localhost.
                                              # Not used with sqlite3.
        'PORT': '',                           # Set to empty string for default.
                                              # Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Europe/Budapest'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'hu'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = '/opt/webadmin/static/'

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
	'/opt/webadmin/cloud/one/static',
	'/opt/webadmin/cloud/cloud/static',
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'sx%4b1oa2)mn%##6+e1+25g@r8ht(cqk(nko^fr66w&amp;26f22ba'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'cloud.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'cloud.wsgi.application'

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.contrib.messages.context_processors.messages',
    'cloud.context_processors.process_debug',
    'cloud.context_processors.process_stat',
    'cloud.context_processors.process_release',
)

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'one',
    'school',
    'cloud',
    'store',
    'firewall',
    'south',
    'djcelery',
    'kombu.transport.django',
    'django_extensions',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
from logging.handlers import SysLogHandler

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
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
        'syslog':{
            'level':'WARNING',
            'class': 'logging.handlers.SysLogHandler',
            'address': '/dev/log',
        },

    },
    'loggers': {
        '': {
            'handlers': ['syslog'],
            'level': 'WARNING',
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}
LOGIN_URL="/login"
AUTH_PROFILE_MODULE = 'school.Person'

import djcelery
djcelery.setup_loader()

CELERY_CACHE_BACKEND = "default"
CELERY_RESULT_BACKEND = "amqp"
CELERY_TASK_RESULT_EXPIRES = 3600

BROKER_URL = 'amqp://nyuszi:teszt@localhost:5672/django'
CELERY_ROUTES = {
    'firewall.tasks.ReloadTask': {'queue': 'local'},
    'firewall.tasks.reload_dns_task': {'queue': 'dns'},
    'firewall.tasks.reload_firewall_task': {'queue': 'firewall'},
    'firewall.tasks.reload_dhcp_task': {'queue': 'dhcp'},
    'firewall.tasks.reload_blacklist_task': {'queue': 'firewall'},
    'firewall.tasks.Periodic': {'queue': 'local'},
    'one.tasks.SendMailTask': {'queue': 'local'},
    'one.tasks.UpdateInstanceStateTask': {'queue': 'local'},
    'one.tasks.UpdateDiskTask': {'queue': 'opennebula'},
    'one.tasks.UpdateNetworkTask': {'queue': 'opennebula'},
    'one.tasks.ChangeInstanceStateTask': {'queue': 'opennebula'},
    'one.tasks.SaveAsTask': {'queue': 'opennebula'},
    'one.tasks.CreateInstanceTask': {'queue': 'opennebula'},
    'one.tasks.DeleteInstanceTask': {'queue': 'opennebula'},

}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
    }
}


store_settings = {
    "basic_auth": "True",
    "verify_ssl": "False",
    "ssl_auth": "False",
    "store_client_pass":  "IQu8Eice",
    "store_client_user":  "admin",
    "store_client_key": "/opt/webadmin/cloud/client.key",
    "store_client_cert": "/opt/webadmin/cloud/client.crt",
    "store_url": "http://localhost:9000",
    "store_public": "store.ik.bme.hu",
}

firewall_settings = {
    "default_vlangroup": "publikus",
    "reload_sleep": "10",
    "dns_hostname": "dns1.ik.bme.hu",
    "rdns_ip": "152.66.243.60",
    "dns_ip": "152.66.243.60",
    "dns_ttl": "300",
}

EMAIL_HOST='152.66.243.92' # giccero ipv4
CLOUD_URL='https://cloud.ik.bme.hu/'
RELEASE='master'

try:
    from cloud.local_settings import *
except:
    pass

# vim: et sw=4 ai fenc=utf8 smarttab :
