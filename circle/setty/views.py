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

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse, reverse_lazy
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from braces.views import LoginRequiredMixin
from django.views.generic import TemplateView, DeleteView
from django_tables2 import SingleTableView
from saltstackhelper import *
from controller import *
from dashboard.views.util import FilterMixin
from django.utils.translation import ugettext as _
import json
import logging


from tables import ServiceListTable
from forms import ServiceListSearchForm

logger = logging.getLogger(__name__)


class DetailView(LoginRequiredMixin, TemplateView):
    template_name = "setty/index.html"
    salthelper = SaltStackHelper()

    def get_context_data(self, **kwargs):
        logger.debug('DetailView.get_context_data() called. User: %s',
                     unicode(self.request.user))
        service = Service.objects.get(id=kwargs['pk'])

        if self.request.user == service.user or self.request.user.is_superuser:
            context = super(DetailView, self).get_context_data(**kwargs)
            context['elementTemplateList'] = ElementTemplate.objects.all()
            context['actualId'] = kwargs['pk']
            return context
        else:
            raise PermissionDenied

    def post(self, request, *args, **kwargs):
        service = Service.objects.get(id=kwargs['pk'])
        if self.request.user != service.user or not self.request.user.is_superuser:
            raise PermissionDenied
            
        result = {}
        eventName = self.request.POST.get('event')
        serviceId = kwargs['pk']
        if eventName == 'loadService':
            result = SettyController.loadService(serviceId)

        elif eventName == "deploy":
            result = SettyController.deploy(serviceId) 

        data = json.loads(self.request.POST.get('data'))

        if eventName == "saveService":
            result = SettyController.saveService(serviceId, data['serviceName'], data[
                                                 'serviceNodes'], data['machines'], data['elementConnections'])
        elif eventName == "getMachineAvailableList":
            result = SettyController.getMachineAvailableList(
                serviceId, data["usedHostnames"])
        elif eventName == "addServiceNode":
            result = SettyController.addServiceNode(
                data["elementTemplateId"])
        elif eventName == "addMachine":
            result = SettyController.addMachine(data["hostname"])
        elif eventName == "getInformation":
            result = SettyController.getInformation(
                data['elementTemplateId'], data['hostname'])

        return JsonResponse(result)


class DeleteView(LoginRequiredMixin, DeleteView):
    model = Service
    success_url = reverse_lazy("dashboard.index")

    def post(self, request, *args, **kwargs):
        logger.debug('DeleteView.post() called. User: %s',
                     unicode(self.request.user))
        service = Service.objects.get(id=kwargs['pk'])

        if self.request.user == service.user or self.request.user.is_superuser:
            return super(DeleteView, self).post(request, *args, **kwargs)
        else:
            return PermissionDenied


class CreateView(LoginRequiredMixin, TemplateView):
    def get_template_names(self):
        if self.request.is_ajax():
            return ['dashboard/_modal.html']
        else:
            return ['dashboard/nojs-wrapper.html']

    def get_context_data(self, *args, **kwargs):
        logger.debug('CreateView.get_context_data() called. User: %s',
                     unicode(self.request.user))
        context = super(CreateView, self).get_context_data(*args, **kwargs)

        context.update({
            'box_title': _('Create service'),
            'ajax_title': True,
            'template': "setty/create-service.html",
        })
        return context

    def post(self, request, *args, **kwargs):
        logger.debug('CreateView.post() called. User: %s',
                     unicode(self.request.user))
        service_name = self.request.POST.get('serviceName')

        if not service_name:
            service_name = "Noname"

        try:
            serviceNameAvailable = Service.objects.get(name=service_name)
            raise PermissionDenied
        except Service.DoesNotExist:
            pass

        service = Service(name=service_name,
                          status=1,
                          user=self.request.user)

        service.save()
        return redirect('setty.views.service-detail', pk=service.pk)


class StartView(LoginRequiredMixin, TemplateView):
    pass


class StopView(LoginRequiredMixin, TemplateView):
    pass


class ListView(LoginRequiredMixin, FilterMixin, SingleTableView):
    template_name = "setty/tables/service-list.html"
    model = Service
    table_class = ServiceListTable
    table_pagination = False

    allowed_filters = {
        'name': "name__icontains",
    }

    def get_context_data(self, *args, **kwargs):
        logger.debug('ListView.get_context_data() called. User: %s',
                     unicode(self.request.user))
        context = super(ListView, self).get_context_data(*args, **kwargs)
        context['search_form'] = self.search_form
        return context

    def get(self, *args, **kwargs):
        logger.debug('ListView.get() called. User: %s',
                     unicode(self.request.user))
        self.search_form = ServiceListSearchForm(self.request.GET)
        self.search_form.full_clean()

        if self.request.is_ajax():
            services = [{
                'url': reverse("setty.views.service-detail",
                               kwargs={'pk': i.pk}),
                'status': i.status,
                'name': i.name} for i in self.get_queryset()]
            return HttpResponse(
                json.dumps(services),
                content_type="application/json",
            )
        else:
            return super(ListView, self).get(*args, **kwargs)

    def get_queryset(self):
        logger.debug('ListView.get_queryset() called. User: %s',
                     unicode(self.request.user))
        qs = self.model.objects.all()
        self.create_fake_get()
        try:
            filters, excludes = self.get_queryset_filters()
            if not self.request.user.is_superuser:
                filters['user'] = self.request.user
            qs = qs.filter(**filters).exclude(**excludes).distinct()
        except ValueError:
            messages.error(self.request, _("Error during filtering."))

        return qs
