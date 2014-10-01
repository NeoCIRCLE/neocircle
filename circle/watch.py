import subprocess
import os
import pyinotify
from django.conf import settings

STATIC_FILES = u'--include-path={}'.format(':'.join(settings.STATICFILES_DIRS))


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


if __name__ == "__main__":
    # for first run compile everything
    print("Initial LESS compiles")
    current_dir = os.path.dirname(os.path.realpath(__file__))

    for root, dirs, files in os.walk("/home/cloud/circle/circle"):
        for f in files:
            if not f.endswith(".less"):
                continue

            relpath = os.path.relpath(root, current_dir)
            if relpath.startswith(("static_collected", "bower_components")):
                continue

            less_pathname = "%s/%s" % (root, f)
            css_pathname = LessUtils.less_path_to_css_path(less_pathname)
            LessUtils.compile_less(less_pathname, css_pathname)

    print("\n%s\n" % ("=" * 30))
    print("End of initial LESS compiles\n")

    # after first run watch less files
    wm = pyinotify.WatchManager()

    class EventHandler(pyinotify.ProcessEvent):
        def process_IN_MODIFY(self, event):
            if not event.name.endswith(".less"):
                return

            css_pathname = LessUtils.less_path_to_css_path(event.pathname)
            LessUtils.compile_less(event.pathname, css_pathname)

    handler = EventHandler()
    notifier = pyinotify.Notifier(wm, handler)
    wm.add_watch(current_dir, pyinotify.IN_MODIFY, rec=True)
    notifier.loop()
