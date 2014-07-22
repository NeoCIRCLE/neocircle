import contextlib
import datetime

from fabric.api import env, run, settings, sudo, prefix, cd
from fabric.decorators import roles

from vm.models import Node
from storage.models import DataStore


def get_hosts():
    env.roledefs['portal'] = ['localhost']

    env.roledefs['nodes'] = [unicode(n.host.ipv4)
                             for n in Node.objects.filter(enabled=True)]
    env.roledefs['storage'] = [DataStore.objects.get().hostname]
    print env.roledefs


def update_all():
    update_node()
    update_portal()


@roles('portal')
def migrate():
    "Run db migrations"
    with _workon("circle"), cd("~/circle/circle"):
        run("./manage.py migrate")


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


@roles('portal')
def compile_things():
    "Compile translation and collect static files"
    compile_js()
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
        run("./manage.py test --settings=circle.settings.test %s" % test)


def pull(dir="~/circle/circle"):
    "Pull from upstream branch (stash any changes)"
    now = unicode(datetime.datetime.now())
    with cd(dir):
        run("git status || git stash save update %s" % now)
        run("git pull --ff-only")


@roles('portal')
def update_portal(test=False):
    "Update and restart portal+manager"
    with _stopped("portal", "mancelery"):
        pull()
        migrate()
        compile_things()
        if test:
            test()


@roles('node')
def update_node():
    "Update and restart nodes"
    with _stopped("node", "agent"):
        pull("~/circle/vmdriver")
        pull("~/circle/agentdriver")


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
    _stop_services(True, *services)
    yield
    _start_services(*services)


def _workon(name):
    return prefix("source ~/.virtualenvs/%s/bin/activate && "
                  "source ~/.virtualenvs/%s/bin/postactivate" % (name, name))
