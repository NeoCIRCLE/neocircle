from base import *  # noqa

########## TEST SETTINGS
TEST_RUNNER = 'discover_runner.DiscoverRunner'
TEST_DISCOVER_TOP_LEVEL = SITE_ROOT
TEST_DISCOVER_ROOT = SITE_ROOT
TEST_DISCOVER_PATTERN = "test_*.py"
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
