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
INSTALLED_APPS += ("debug_toolbar", )
MIDDLEWARE_CLASSES += ("debug_toolbar.middleware.DebugToolbarMiddleware", )
