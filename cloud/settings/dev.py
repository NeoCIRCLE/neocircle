# coding=utf8
# Django development settings for cloud project.
from .base import *  # NOQA

DEBUG = True
TEMPLATE_DEBUG = DEBUG
EMAIL_HOST = "localhost"
EMAIL_PORT = 1025

ADMINS = (
    ('Ory, Mate', 'orymate@localhost'),
)
MANAGERS = (
    ('Ory Mate', 'maat@localhost'),
)
#INSTALLED_APPS += ("debug_toolbar", )
#MIDDLEWARE_CLASSES += ("debug_toolbar.middleware.DebugToolbarMiddleware", )
INTERNAL_IPS = [('2001:738:2001:4031:5:253:%d:0' % i) for i in xrange(1, 100)]
INTERNAL_IPS += [('10.5.253.%d' % i) for i in xrange(1, 100)]
CRISPY_FAIL_SILENTLY = False
