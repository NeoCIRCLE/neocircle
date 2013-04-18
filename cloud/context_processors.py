import json
import subprocess

from django.conf import settings
from django.core.cache import cache

def process_debug(req):
    return {'DEBUG': settings.DEBUG}

def process_stat(req):
    if settings.STAT_DEBUG:
        stat = {
            'CPU': {
                'USED_CPU': 10,
                'ALLOC_CPU': 20,
                'FREE_CPU': 70
            },
            'MEM': {
                'USED_MEM': 567,
                'ALLOC_MEM': 371,
                'FREE_MEM': 2048-567-371
            }
        }
    else:
        stat = cache.get('cloud_stat')
    return {
        'STAT_DEBUG': settings.STAT_DEBUG,
        'cloud_stat': stat,
    }

def process_release(req):
    return {
        'release': settings.RELEASE,
    }
