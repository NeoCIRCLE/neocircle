from django.core.management.base import BaseCommand, CommandError
from one.models import *

class Command(BaseCommand):
    args = None
    help = 'Update status of One resources'

    def handle(self, *args, **options):
        Disk.update()
        Network.update()
