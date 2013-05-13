from one.models import *
from one.tasks import GetInstanceStateTask
from django_extensions.management.jobs import HourlyJob

class Job(HourlyJob):
    help = "Update Disks, Networks and Instances from OpenNebula."

    def execute(self):
        Disk.update()
        Network.update()
        for i in Instance.objects.filter(state__in=['ACTIVE', 'STOPPED'], time_of_delete__isnull=False, waiting=True):
            GetInstanceStateTask.delay(i.one_id)
        pass
