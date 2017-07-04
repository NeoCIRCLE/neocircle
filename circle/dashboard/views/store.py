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
from __future__ import unicode_literals, absolute_import

import json
import logging
from os.path import join, normpath, dirname, basename

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.template.defaultfilters import urlencode
from django.core.cache import cache
from django.core.exceptions import SuspiciousOperation
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import redirect, render_to_response, render
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import TemplateView

from braces.views import LoginRequiredMixin

from ..store_api import Store, NoStoreException, NotOkException

logger = logging.getLogger(__name__)


class StoreList(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/store/list.html"

    def get_context_data(self, **kwargs):
        context = super(StoreList, self).get_context_data(**kwargs)
        directory = self.request.GET.get("directory", "/")
        directory = "/" if not len(directory) else directory

        store = Store(self.request.user)
        context['root'] = store.list(directory)
        context['quota'] = store.get_quota()
        context['up_url'] = self.create_up_directory(directory)
        context['current'] = directory
        context['next_url'] = "%s%s?directory=%s" % (
            settings.DJANGO_URL.rstrip("/"),
            reverse("dashboard.views.store-list"), urlencode(directory))
        return context

    def get(self, *args, **kwargs):
        try:
            if self.request.is_ajax():
                context = self.get_context_data(**kwargs)
                return render_to_response(
                    "dashboard/store/_list-box.html",
                    RequestContext(self.request, context).flatten(),
                )
            else:
                return super(StoreList, self).get(*args, **kwargs)
        except NoStoreException:
            messages.warning(self.request, _("No store."))
        except NotOkException:
            messages.warning(self.request, _("Store has some problems now."
                                             " Try again later."))
        except Exception as e:
            logger.critical("Something is wrong with store: %s", unicode(e))
            messages.warning(self.request, _("Unknown store error."))
        return redirect("/")

    def create_up_directory(self, directory):
        path = normpath(join('/', directory, '..'))
        if not path.endswith("/"):
            path += "/"
        return path


@require_GET
@login_required
def store_download(request):
    path = request.GET.get("path")
    try:
        url = Store(request.user).request_download(path)
    except Exception:
        messages.error(request, _("Something went wrong during download."))
        logger.exception("Unable to download, "
                         "maybe it is already deleted")
        return redirect(reverse("dashboard.views.store-list"))
    return redirect(url)


@require_GET
@login_required
def store_upload(request):
    directory = request.GET.get("directory", "/")
    try:
        action = Store(request.user).request_upload(directory)
    except Exception:
        logger.exception("Unable to upload")
        messages.error(request, _("Unable to upload file."))
        return redirect("/")

    next_url = "%s%s?directory=%s" % (
        settings.DJANGO_URL.rstrip("/"),
        reverse("dashboard.views.store-list"), urlencode(directory))

    return render(request, "dashboard/store/upload.html",
                  {'directory': directory, 'action': action,
                   'next_url': next_url})


@require_GET
@login_required
def store_get_upload_url(request):
    current_dir = request.GET.get("current_dir")
    try:
        url = Store(request.user).request_upload(current_dir)
    except Exception:
        logger.exception("Unable to upload")
        messages.error(request, _("Unable to upload file."))
        return redirect("/")
    return HttpResponse(
        json.dumps({'url': url}), content_type="application/json")


class StoreRemove(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/store/remove.html"

    def get_context_data(self, *args, **kwargs):
        context = super(StoreRemove, self).get_context_data(*args, **kwargs)
        path = self.request.GET.get("path", "/")
        if path == "/":
            SuspiciousOperation()

        context['path'] = path
        context['is_dir'] = path.endswith("/")
        if context['is_dir']:
            context['directory'] = path
        else:
            context['directory'] = dirname(path)
            context['name'] = basename(path)

        return context

    def get(self, *args, **kwargs):
        try:
            return super(StoreRemove, self).get(*args, **kwargs)
        except NoStoreException:
            return redirect("/")

    def post(self, *args, **kwargs):
        path = self.request.POST.get("path")
        try:
            Store(self.request.user).remove(path)
        except Exception:
            logger.exception("Unable to remove %s", path)
            messages.error(self.request, _("Unable to remove %s.") % path)

        return redirect("%s?directory=%s" % (
            reverse("dashboard.views.store-list"),
            urlencode(dirname(dirname(path))),
        ))


@require_POST
@login_required
def store_new_directory(request):
    path = request.POST.get("path")
    name = request.POST.get("name")

    try:
        Store(request.user).new_folder(join(path, name))
    except Exception:
        logger.exception("Unable to create folder %s in %s for %s",
                         name, path, unicode(request.user))
        messages.error(request, _("Unable to create folder."))
    return redirect("%s?directory=%s" % (
        reverse("dashboard.views.store-list"), urlencode(path)))


@require_POST
@login_required
def store_refresh_toplist(request):
    cache_key = "files-%d" % request.user.pk
    try:
        store = Store(request.user)
        toplist = store.toplist()
        quota = store.get_quota()
        files = {'toplist': toplist, 'quota': quota}
    except Exception:
        logger.exception("Can't get toplist of %s", unicode(request.user))
        files = {'toplist': []}
    cache.set(cache_key, files, 300)

    return redirect(reverse("dashboard.index"))
