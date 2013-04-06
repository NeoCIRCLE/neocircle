from one.models import *
from django_extensions.management.jobs import QuarterHourlyJob
from django.core.cache import cache
import json

class Job(QuarterHourlyJob):
    help = "Update statistics from OpenNebula."

    def execute(self):
        stat = json.loads(subprocess.check_output(['/opt/webadmin/cloud/miscellaneous/stat/stat_wrap.sh']))
        cache.set('cloud_stat', stat)

