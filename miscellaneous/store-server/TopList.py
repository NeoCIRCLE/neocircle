import os, os.path
from pyinotify import WatchManager, Notifier, ThreadedNotifier, EventsCodes, ProcessEvent, IN_DONT_FOLLOW, IN_CREATE, IN_MODIFY
import pwd

COUNT=5

wm = WatchManager()
mask = IN_CREATE | IN_MODIFY | IN_DONT_FOLLOW

"""
Register given file to ~/../.top dir as a symbolic link.
"""
def update_new(name):
    if os.path.normpath(name).find("/.") != -1:
        return
    home = pwd.getpwuid(os.stat(name).st_uid).pw_dir
    if not name.startswith(home):
        return # outside home

    top_dir = os.path.normpath(os.path.join(home, "../.top"))
    try:
        os.mkdir(top_dir)
    except OSError:
        for f in os.listdir(top_dir):
            if os.readlink(os.path.join(top_dir, f)) == name:
                return # duplicate

    for i in range(1, COUNT):
        try:
            os.rename(os.path.join(top_dir, str(i+1)), os.path.join(top_dir, str(i)))
        except OSError as e:
            pass

    os.symlink(name, os.path.join(top_dir, str(COUNT)))

"""
Process inotify event.
"""
class Process(ProcessEvent):
    def process_default(self, event):
        if event.name:
            update_new(os.path.join(event.path, event.name))

"""
Watch continuously file modifications in /home.
"""
def main():
    notifier = Notifier(wm, Process())
    wdd = wm.add_watch('/home', mask, rec=True)
    while True:  # loop forever
        try:
            # process the queue of events as explained above
            notifier.process_events()
            if notifier.check_events():
                # read notified events and enqeue them
                notifier.read_events()
        except KeyboardInterrupt:
            # destroy the inotify's instance on this interrupt (stop monitoring)
            notifier.stop()
            break

if __name__ == "__main__":
        main()
