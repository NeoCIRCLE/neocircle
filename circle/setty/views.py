from django.template import RequestContext
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, DeleteView
from django.core.urlresolvers import reverse_lazy
from django.db.models import Q
from django.http import HttpResponseForbidden, Http404
from django.shortcuts import redirect
from django.contrib import auth
from .models import (
    Element,
    ElementTemplate,
    ElementConnection,
    Service
)
import json


class IndexView(TemplateView):
    template_name = "setty/index.html"

    def get(self, request, *args, **kwargs):
        if self.request.user.is_authenticated():
            return TemplateView.get(self, request, *args, **kwargs)  # To be checked!
        else:
            return redirect(auth.views.login)

    def get_context_data(self, **kwargs):
        elementTemplateList = ElementTemplate.objects.all()
        context = RequestContext(
            self.request,
            {'elementTemplateList': elementTemplateList})
        return context

    @csrf_exempt
    def post(self, request, *args, **kwargs):
        if self.request.POST.get('event') == "saveService":
            jsonData = json.loads(self.request.POST.get('data'))

            serviceName = jsonData['serviceName']

            if 'pk' in kwargs:
                serviceObject = Service.objects.get(id=kwargs['pk'])
                serviceObject.name = serviceName
                serviceObject.save()

                Element.objects.filter(service=serviceObject).delete()

            else:
                serviceObject = Service(
                    name=serviceName,
                    user=self.request.user
                )
                serviceObject.save()

            for element in jsonData['elements']:
                elementObject = Element(
                    service=serviceObject,
                    parameters="none",  # further plan
                    display_id=element['displayId'],
                    pos_x=element['posX'],
                    pos_y=element['posY'],
                    anchors=element['anchors']
                )
                elementObject.save()

            for elementConnection in jsonData['elementConnections']:
                sourceId = elementConnection['sourceId']
                targetId = elementConnection['targetId']
                sourceEndpoint = elementConnection['sourceEndpoint']
                targetEndpoint = elementConnection['targetEndpoint']
                connectionParameters = elementConnection['parameters']

                targetObject = Element.objects.get(
                    display_id=targetId,
                    service=serviceObject)

                sourceObject = Element.objects.get(
                    display_id=sourceId,
                    service=serviceObject)

                connectionObject = ElementConnection(
                    target=targetObject,
                    source=sourceObject,
                    target_endpoint=targetEndpoint,
                    source_endpoint=sourceEndpoint,
                    parameters=connectionParameters
                )
                connectionObject.save()

            return HttpResponse(serviceObject.pk)

        else:
            return HttpResponse()


class DeleteView(DeleteView):
    model = Service

    success_url = reverse_lazy("dashboard.index")


class StartView(TemplateView):
    pass


class ListView(TemplateView):
    pass


class DetailView(IndexView):
    def get(self, request, *args, **kwargs):
        try:
            serviceObject = Service.objects.get(id=kwargs['pk'])
            if serviceObject.user != self.request.user:
                return HttpResponseForbidden("You don't have permission to open the service.")
        except:
            raise Http404
        else:
            return IndexView.get(self, request, *args, **kwargs)

    @csrf_exempt
    def post(self, request, *args, **kwargs):
        if self.request.POST.get('event') == "loadService":
            serviceObject = Service.objects.get(id=kwargs['pk'])
            elementList = Element.objects.filter(service=serviceObject)
            elementConnectionList = ElementConnection.objects.filter(
                Q(target__in=elementList) | Q(source__in=elementList))

            elements = []
            elementConnections = []

            for item in elementList:
                elements.append({
                    'parameters': item.parameters,
                    'displayId': item.display_id,
                    'posX': item.pos_x,
                    'posY': item.pos_y,
                    'anchors': item.anchors
                })

            for item in elementConnectionList:
                elementConnections.append({
                    'targetEndpoint': item.target_endpoint,
                    'sourceEndpoint': item.source_endpoint,
                    'parameters': item.parameters
                })

            return HttpResponse(json.dumps(
                {"elements": elements,
                 "elementConnections": elementConnections,
                 "serviceName": serviceObject.name}))

        else:
            return IndexView.post(self, request, *args, **kwargs)
