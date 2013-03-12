from cloud.settings import DEBUG, STAT_DEBUG, RELEASE
from django.core.cache import cache
import subprocess
import json

def process_debug(req):
    return {'DEBUG': DEBUG}

def process_stat(req):
    stat = cache.get('cloud_stat')
    return {
        'STAT_DEBUG': STAT_DEBUG,
        'cloud_stat': stat,
    }

def process_release(req):
    return {
        'release': RELEASE,
    }
