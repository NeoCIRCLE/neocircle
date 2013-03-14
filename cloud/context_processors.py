from cloud.settings import DEBUG, STAT_DEBUG, RELEASE
from django.core.cache import cache
import subprocess
import json

def process_debug(req):
    return {'DEBUG': DEBUG}

def process_stat(req):
    if STAT_DEBUG:
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
        'STAT_DEBUG': STAT_DEBUG,
        'cloud_stat': stat,
    }

def process_release(req):
    return {
        'release': RELEASE,
    }
