from django.core.management.base import BaseCommand
from .. import create_levels


class Command(BaseCommand):
    args = ''
    help = 'Regenerates Levels'

    def handle(self, *args, **options):
        create_levels(None, None, 3)
