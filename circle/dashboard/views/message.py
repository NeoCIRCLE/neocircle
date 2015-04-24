from django.contrib.messages.views import SuccessMessageMixin
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.views.generic import CreateView, DeleteView, UpdateView

from braces.views import SuperuserRequiredMixin, LoginRequiredMixin
from django_tables2 import SingleTableView

from ..forms import MessageForm
from ..models import Message
from ..tables import MessageListTable


class MessageList(LoginRequiredMixin, SuperuserRequiredMixin, SingleTableView):
    template_name = "dashboard/message-list.html"
    model = Message
    table_class = MessageListTable


class MessageDetail(LoginRequiredMixin, SuperuserRequiredMixin,
                    SuccessMessageMixin, UpdateView):
    model = Message
    template_name = "dashboard/message-edit.html"
    form_class = MessageForm
    success_message = _("Broadcast message successfully updated.")


class MessageCreate(LoginRequiredMixin, SuperuserRequiredMixin,
                    SuccessMessageMixin, CreateView):
    model = Message
    template_name = "dashboard/message-create.html"
    form_class = MessageForm
    success_message = _("New broadcast message successfully created.")


class MessageDelete(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = Message
    template_name = "dashboard/confirm/base-delete.html"

    def get_success_url(self):
        return reverse("dashboard.views.message-list")
