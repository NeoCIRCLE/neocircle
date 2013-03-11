from cloud.settings import DEBUG, STAT_DEBUG
from django.core.cache import cache
import subprocess
import json

def process_debug(req):
    return {'DEBUG': DEBUG}

def process_stat(req):
    # stat = cache.get('cloud_stat');
    stat = json.loads(subprocess.check_output(['/opt/webadmin/cloud/miscellaneous/stat/stat_wrap.sh']))
    return {
        'STAT_DEBUG': STAT_DEBUG,
        'cloud_stat': stat,
    }

