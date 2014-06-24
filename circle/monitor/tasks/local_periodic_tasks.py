# Copyright 2014 Budapest University of Technology and Economics (BME IK)
#
# This file is part of CIRCLE Cloud.
#
# CIRCLE is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# CIRCLE is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along
# with CIRCLE.  If not, see <http://www.gnu.org/licenses/>.

import logging
import requests
from time import time

from django.conf import settings
from manager.mancelery import celery

from monitor.client import Client

logger = logging.getLogger(__name__)


@celery.task(ignore_result=True)
def measure_response_time():
    r = requests.get(settings.DJANGO_URL, verify=False)
    total_miliseconds = (
        r.elapsed.seconds * 10**6 +
        r.elapsed.microseconds) / 1000

    Client().send([
        "%(name)s %(val)d %(time)s" % {
            'name': "portal.response_time",
            'val': total_miliseconds,
            'time': time(),
        }
    ])
