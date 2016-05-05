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
from .models import Element, ElementTemplate, ElementConnection, Service
from dashboard.views.util import FilterMixin
from django.utils.translation import ugettext as _
import json
import logging


from tables import ServiceListTable
from forms import ServiceListSearchForm

logger = logging.getLogger(__name__)


class DetailView(LoginRequiredMixin, TemplateView):
    template_name = "setty/index.html"

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
        logger.debug('DetailView.post() called. User: %s',
                     unicode(self.request.user))
        service = Service.objects.get(id=kwargs['pk'])

        if self.request.user == service.user or self.request.user.is_superuser:
            if self.request.POST.get('event') == "saveService":
                data = json.loads(self.request.POST.get('data'))
                service = Service.objects.get(id=kwargs['pk'])
                service.name = data['serviceName']
                service.save()

                Element.objects.filter(service=service).delete()

                for element in data['elements']:
                    elementObject = Element(
                        service=service,
                        parameters=element['parameters'],
                        display_id=element['displayId'],
                        position_left=element['positionLeft'],
                        position_top=element['positionTop'],
                        anchor_number=element['anchorNumber']
                    )
                    elementObject.save()

                for elementConnection in data['elementConnections']:
                    sourceId = elementConnection['sourceId']
                    targetId = elementConnection['targetId']
                    sourceEndpoint = elementConnection['sourceEndpoint']
                    targetEndpoint = elementConnection['targetEndpoint']
                    connectionParameters = elementConnection['parameters']

                    targetObject = Element.objects.get(
                        display_id=targetId,
                        service=service)

                    sourceObject = Element.objects.get(
                        display_id=sourceId,
                        service=service)

                    connectionObject = ElementConnection(
                        target=targetObject,
                        source=sourceObject,
                        target_endpoint=targetEndpoint,
                        source_endpoint=sourceEndpoint,
                        parameters=connectionParameters
                    )
                    connectionObject.save()

                return JsonResponse({'serviceName': service.name})

            elif self.request.POST.get('event') == "loadService":
                service = Service.objects.get(id=kwargs['pk'])
                elementList = Element.objects.filter(service=service)
                elementConnectionList = ElementConnection.objects.filter(
                    Q(target__in=elementList) | Q(source__in=elementList))

                elements = []
                elementConnections = []

                for item in elementList:
                    elements.append({
                        'parameters': item.parameters,
                        'displayId': item.display_id,
                        'positionLeft': item.position_left,
                        'positionTop': item.position_top,
                        'anchorNumber': item.anchor_number})

                for item in elementConnectionList:
                    elementConnections.append({
                        'targetEndpoint': item.target_endpoint,
                        'sourceEndpoint': item.source_endpoint,
                        'parameters': item.parameters})

                return JsonResponse(
                    {'elements': elements,
                     'elementConnections': elementConnections,
                     'serviceName': service.name})

            else:
                raise PermissionDenied
        else:
            raise PermissionDenied


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

        service = Service(
            name=service_name,
            status="stopped",
            user=self.request.user
        )
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
