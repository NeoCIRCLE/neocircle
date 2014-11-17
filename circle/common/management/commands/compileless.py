from django.core.management.base import BaseCommand

from common.management.commands.watch import LessUtils


class Command(BaseCommand):
    help = "Compiles all LESS files."

    def handle(self, *args, **kwargs):
        print("Compiling LESS")
        LessUtils.initial_compile()
