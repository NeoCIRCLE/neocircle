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

from django.contrib.messages.views import SuccessMessageMixin
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.views.generic import CreateView, DeleteView, UpdateView

from braces.views import SuperuserRequiredMixin, LoginRequiredMixin
from django_tables2 import SingleTableView

from ..forms import MessageForm
from ..models import Message
from ..tables import MessageListTable


class InvalidateMessageCacheMixin(object):
    def post(self, *args, **kwargs):
        key = make_template_fragment_key('broadcast_messages')
        cache.delete(key)
        return super(InvalidateMessageCacheMixin, self).post(*args, **kwargs)


class MessageList(LoginRequiredMixin, SuperuserRequiredMixin, SingleTableView):
    template_name = "dashboard/message-list.html"
    model = Message
    table_class = MessageListTable


class MessageDetail(InvalidateMessageCacheMixin, LoginRequiredMixin,
                    SuperuserRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Message
    template_name = "dashboard/message-edit.html"
    form_class = MessageForm
    success_message = _("Broadcast message successfully updated.")


class MessageCreate(InvalidateMessageCacheMixin, LoginRequiredMixin,
                    SuperuserRequiredMixin, SuccessMessageMixin, CreateView):
    model = Message
    template_name = "dashboard/message-create.html"
    form_class = MessageForm
    success_message = _("New broadcast message successfully created.")


class MessageDelete(InvalidateMessageCacheMixin, LoginRequiredMixin,
                    SuperuserRequiredMixin, DeleteView):
    model = Message
    template_name = "dashboard/confirm/base-delete.html"

    def get_success_url(self):
        return reverse("dashboard.views.message-list")
