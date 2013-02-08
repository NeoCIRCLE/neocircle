from django_extensions.management.jobs import HourlyJob

class Job(HourlyJob):
    help = "Suspend/delete expired Instances."

    def execute(self):
        # executing empty sample job TODO
        pass
