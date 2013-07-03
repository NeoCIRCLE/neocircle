# coding=utf8
# Django production settings for cloud project.
from .base import *  # NOQA

DEBUG = False
TEMPLATE_DEBUG = DEBUG
STORE_SETTINGS['store_url'] = 'https://store.cloud.ik.bme.hu'
STORE_SETTINGS['ssl_auth'] = 'True'
STORE_SETTINGS['store_host'] = 'store.cloud.ik.bme.hu'
