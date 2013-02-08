from one.models import *
from django_extensions.management.jobs import HourlyJob

class Job(HourlyJob):
    help = "Update Disks and Networks from OpenNebula."

    def execute(self):
        Disk.update()
        Network.update()
        pass
