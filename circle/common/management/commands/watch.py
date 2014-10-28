import subprocess
import os
import pyinotify

from django.core.management.base import BaseCommand
from django.conf import settings

STATIC_FILES = u'--include-path={}'.format(':'.join(settings.STATICFILES_DIRS))
IGNORED_FOLDERS = ("static_collected", "bower_components", )


class LessUtils(object):
    @staticmethod
    def less_path_to_css_path(pathname):
        return "%s.css" % pathname[:-1 * len(".less")]

    @staticmethod
    def compile_less(less_pathname, css_pathname):
        cmd = ["lessc", STATIC_FILES, less_pathname, css_pathname]

        print("\n%s" % ("=" * 30))
        print("Compiling: %s" % os.path.basename(less_pathname))

        try:
            subprocess.check_output(cmd)
        except subprocess.CalledProcessError as e:
            print(e.output)
        else:
            print("Successfully compiled:\n%s\n->\n%s" % (
                less_pathname, css_pathname))

    @staticmethod
    def initial_compile():
        """ Walks through the project looking for LESS files
        and compiles them into CSS.
        """
        for root, dirs, files in os.walk(settings.SITE_ROOT):
            for f in files:
                if not f.endswith(".less"):
                    continue

                relpath = os.path.relpath(root, settings.SITE_ROOT)
                if relpath.startswith(IGNORED_FOLDERS):
                    continue

                less_pathname = "%s/%s" % (root, f)
                css_pathname = LessUtils.less_path_to_css_path(less_pathname)
                LessUtils.compile_less(less_pathname, css_pathname)

    @staticmethod
    def start_watch():
        """ Watches for changes in LESS files recursively from the
        project's root and compiles the files
        """
        wm = pyinotify.WatchManager()

        class EventHandler(pyinotify.ProcessEvent):
            def process_IN_MODIFY(self, event):
                if not event.name.endswith(".less"):
                    return

                relpath = os.path.relpath(event.pathname, settings.SITE_ROOT)
                if relpath.startswith(IGNORED_FOLDERS):
                    return

                css_pathname = LessUtils.less_path_to_css_path(event.pathname)
                LessUtils.compile_less(event.pathname, css_pathname)

        handler = EventHandler()
        notifier = pyinotify.Notifier(wm, handler)
        wm.add_watch(settings.SITE_ROOT, pyinotify.IN_MODIFY, rec=True)
        notifier.loop()


class Command(BaseCommand):
    help = "Compiles all LESS files then watches for changes."

    def handle(self, *args, **kwargs):
        # for first run compile everything
        print("Initial LESS compiles")
        LessUtils.initial_compile()
        print("\n%s\n" % ("=" * 30))
        print("End of initial LESS compiles\n")

        # after first run watch less files
        LessUtils.start_watch()
