#!/bin/echo Usage: fab --list -f

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

import contextlib
import datetime

from fabric.api import env, run, settings, sudo, prefix, cd, execute
from fabric.context_managers import shell_env
from fabric.decorators import roles, parallel


env.roledefs['portal'] = ['localhost']

try:
    import django
    django.setup()
    from vm.models import Node as _Node
    from storage.models import DataStore as _DataStore
except Exception as e:
    print e
else:
    env.roledefs['node'] = [unicode(n.host.ipv4)
                            for n in _Node.objects.filter(enabled=True)]
    env.roledefs['storage'] = [_DataStore.objects.get().hostname]


def update_all():
    "Update and restart portal+manager, nodes and storage"
    execute(stop_portal)
    execute(parallel(update_node))
    execute(update_storage)
    execute(update_portal)


def pip(env, req):
    "Install pip requirements"
    with _workon(env):
        run("pip install -r %s" % req)


def bower(component=None):
    "Install bower component"
    with cd("~/circle/circle"):
        if component:
            run("bower install %s --config.interactive=false" % component)
        else:
            run("bower install --config.interactive=false")


@roles('portal')
def flake8():
    "Run portal tests"
    with _workon("circle"), cd("~/circle/circle"):
        run("flake8 . --exclude=migrations,bower_components,"
            "south_migrations,static_collected --max-complexity 12")


@roles('portal')
def migrate():
    "Run db migrations"
    with _workon("circle"), cd("~/circle/circle"):
        run("./manage.py migrate --fake-initial")


@roles('portal')
def compile_js():
    "Generate JS translation objects"
    with _workon("circle"), cd("~/circle/circle"):
        run("./manage.py compilejsi18n -o dashboard/static/jsi18n")


@roles('portal')
def collectstatic():
    "Collect static files"
    with _workon("circle"), cd("~/circle/circle"):
        run("./manage.py collectstatic --noinput")


@roles('portal')
def compile_messages():
    "Generate MO translation objects"
    with _workon("circle"), cd("~/circle/circle"):
        run("./manage.py compilemessages")


def compile_less():
    "Compile LESS files"
    with _workon("circle"), cd("~/circle/circle"):
        run("./manage.py compileless")


@roles('portal')
def compile_things():
    "Compile translation and collect static files"
    compile_js()
    compile_less()
    collectstatic()
    compile_messages()


@roles('portal')
def make_messages():
    "Update PO translation templates and commit"
    with _workon("circle"), cd("~/circle/circle"):
        run("git status")
        run("./manage.py makemessages -d djangojs -a --ignore=jsi18n/*")
        run("./manage.py makemessages -d django -a")
        run("git commit -avm 'update PO templates'")


@roles('portal')
def test(test=""):
    "Run portal tests"
    with _workon("circle"), cd("~/circle/circle"):
        if test == "f":
            test = "--failed"
        else:
            test += " --with-id"
        run("./manage.py test --settings=circle.settings.test %s" % test)


@roles('portal')
def selenium(test=""):
    "Run selenium tests"
    with _workon("circle"), cd("~/circle/circle"):
        if test == "f":
            test = "--failed"
        else:
            test += " --with-id"
        run('xvfb-run --server-args="-screen 0, 1920x1080x24" ./manage.py'
            ' test --settings=circle.settings.selenium_test %s' % test)


def pull(dir="~/circle/circle"):
    "Pull from upstream branch (stash any changes)"
    now = unicode(datetime.datetime.now())
    with cd(dir), shell_env(GIT_AUTHOR_NAME="fabric",
                            GIT_AUTHOR_EMAIL="fabric@local",
                            GIT_COMMITTER_NAME="fabric",
                            GIT_COMMITTER_EMAIL="fabric@local"):
        run("git stash save update %s" % now)
        run("git pull --ff-only")


@roles('portal')
def update_portal(test=False, git=True):
    "Update and restart portal+manager"
    with _stopped("portal", "manager"):
        if git:
            pull()
        cleanup()
        pip("circle", "~/circle/requirements.txt")
        sudo("cp ~/circle/miscellaneous/*celery.conf /etc/init/")
        bower()
        migrate()
        compile_things()
        if test:
            test()


@roles('portal')
def build_portal():
    "Update portal without pulling from git"
    return update_portal(False, False)


@roles('portal')
def stop_portal(test=False):
    "Stop portal and manager"
    _stop_services("portal", "manager")


@roles('node')
def update_node():
    "Update and restart nodes"
    with _stopped("node", "agentdriver", "monitor-client"):
        pull("~/vmdriver")
        pip("vmdriver", "~/vmdriver/requirements/production.txt")
        _cleanup("~/vmdriver")

        pull("~/agentdriver")
        pip("agentdriver", "~/agentdriver/requirements.txt")
        _cleanup("~/agentdriver")

        pull("~/monitor-client")
        pip("monitor-client", "~/monitor-client/requirements.txt")
        _cleanup("~/monitor-client")


@parallel
@roles('storage')
def update_storage():
    "Update and restart storagedriver"
    with _stopped("storage"):
        pull("~/storagedriver")
        pip("storagedriver", "~/storagedriver/requirements/production.txt")


@parallel
@roles('node')
def checkout(vmdriver="master", agent="master"):
    """Checkout specific branch on nodes"""
    with settings(warn_only=True), cd("~/vmdriver"):
        run("git checkout %s" % vmdriver)
    with settings(warn_only=True), cd("~/agentdriver"):
        run("git checkout %s" % agent)


@roles('portal')
def cleanup():
    "Clean pyc files of portal"
    _cleanup()


def _cleanup(dir="~/circle/circle"):
    "Clean pyc files"
    with cd(dir):
        run("find -name '*.py[co]' -exec rm -f {} +")


def _stop_services(*services):
    "Stop given services (warn only if not running)"
    with settings(warn_only=True):
        for service in reversed(services):
            sudo("stop %s" % service)


def _start_services(*services):
    for service in services:
        sudo("start %s" % service)


def _restart_service(*services):
    "Stop and start services"
    _stop_services(*services)
    _start_services(*services)


@contextlib.contextmanager
def _stopped(*services):
    _stop_services(*services)
    yield
    _start_services(*services)


def _workon(name):
    return prefix("source ~/.virtualenvs/%s/bin/activate && "
                  "source ~/.virtualenvs/%s/bin/postactivate" % (name, name))


@roles('portal')
def install_bash_completion_script():
    sudo("wget https://raw.githubusercontent.com/marcelor/fabric-bash-"
         "autocompletion/48baf5735bafbb2be5be8787d2c2c04a44b6cdb0/fab "
         "-O /etc/bash_completion.d/fab")
    print("To have bash completion instantly, run\n"
          "  source /etc/bash_completion.d/fab")
