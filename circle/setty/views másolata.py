from django.template import RequestContext, loader
from django.http import HttpResponse
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from .models import (
    Element,
    ElementTemplate,
    ElementConnection,
    Service,
    User,
)
import json


class IndexView(TemplateView):
    template_name = "setty/index.html"

    def get_context_data(self, **kwargs):
        pass


@csrf_exempt
def index(request):
    if request.method == 'POST':
        if request.POST.get('event') == "getLoggedInUser":
            username = None
            if request.user.is_authenticated():
                return HttpResponse(request.user.username)
            else:
                return HttpResponse("unauthenticated!")

        elif request.POST.get('event') == "deleteConfig":
            try:
                siteUser = User.objects.get(name=request.POST.get('user'))
                workSpace = Workspace.objects.get(
                    name=request.POST.get('data'),
                    user=siteUser,
                )

                serviceInstances = ServiceInstance.objects.all().filter(
                    workspace=workSpace,
                )

                for instance in serviceInstances:
                    connectionTargets = ServiceConnection.objects.all().filter(
                        target=instance,
                    )
                    connectionSources = ServiceConnection.objects.all().filter(
                        source=instance,
                    )

                    for connection in connectionSources:
                        connection.delete()

                    for connection in connectionTargets:
                        connection.delete()

                    instance.delete()

                workSpace.delete()

                return HttpResponse(
                    "Workspace (" +
                    request.POST.get('data') +
                    ") deleted successfully."
                )

            except:
                return HttpResponse(
                    "Failed deleting workspace (" +
                    request.POST.get('data') +
                    ")."
                )

        elif request.POST.get('event') == "saveConfig":
            jsonData = json.loads(request.POST.get('data'))

            userName = jsonData['exportData']['user']

            try:
                siteUser = User.objects.get(name=userName)
            except User.DoesNotExist:
                siteUser = User(name=userName)
                siteUser.save()

            try:
                siteWorkspace = Workspace.objects.get(
                    name=jsonData['exportData']['workspace'],
                    user=siteUser,
                )
                siteWorkspace.delete()
                siteWorkspace = Workspace(
                    user=siteUser,
                    name=jsonData['exportData']['workspace'],
                )
                siteWorkspace.save()
            except Workspace.DoesNotExist:
                siteWorkspace = Workspace(
                    user=siteUser,
                    name=jsonData['exportData']['workspace'],
                )
                siteWorkspace.save()

            for connection in jsonData['exportData']['connections']:
                tempData = jsonData['exportData']['connections']

                sourceId = tempData[connection]['sourceid']
                targetId = tempData[connection]['targetid']
                sourcePosX = tempData[connection]['sourceposx']
                sourcePosY = tempData[connection]['sourceposy']
                targetPosX = tempData[connection]['targetposx']
                targetPosY = tempData[connection]['targetposy']
                sourceendpoint = tempData[connection]['sourceendpoint']
                targetendpoint = tempData[connection]['targetendpoint']
                targetParent = Service.objects.get(id=targetId)
                sourceParent = Service.objects.get(id=sourceId)
                serviceInstanceSource = ServiceInstance(
                    parentservice=sourceParent,
                    workspace=siteWorkspace,
                    parameters=Service.objects.get(id=sourceId).configuration,
                    posX=sourcePosX,
                    posY=sourcePosY,
                )
                serviceInstanceSource.save()

                serviceInstanceTarget = ServiceInstance(
                    parentservice=targetParent,
                    workspace=siteWorkspace,
                    parameters=Service.objects.get(id=targetId).configuration,
                    posX=targetPosX,
                    posY=targetPosY,
                )
                serviceInstanceTarget.save()

                serviceConnection = ServiceConnection(
                    target=serviceInstanceTarget,
                    source=serviceInstanceSource,
                    sourceEndpoint=sourceendpoint,
                    targetEndpoint=targetendpoint,
                    parameters='Not yet configured',
                )
                serviceConnection.save()

            print jsonData
            return HttpResponse(siteWorkspace.name)

        elif request.POST.get('event') == "loadConfig":
            i = 0
            data = []

            siteUser = User.objects.get(name=request.POST.get('user'))
            workSpace = Workspace.objects.get(
                name=request.POST.get('data'),
                user=siteUser,
            )

            connectionList = ServiceConnection.objects.all().filter(
                Q(source__workspace=workSpace) |
                Q(target__workspace=workSpace)
            )

            for connection in connectionList:
                ++i
                seged = {}

                seged['targetposx'] = connection.target.posX
                seged['targetposy'] = connection.target.posY
                seged['targetendpoint'] = connection.targetEndpoint
                seged['targetid'] = connection.target.parentservice.id
                seged['sourceposx'] = connection.source.posX
                seged['sourceposy'] = connection.source.posY
                seged['sourceendpoint'] = connection.sourceEndpoint
                seged['sourceid'] = connection.source.parentservice.id

                data.append(seged)

            jsonData = json.dumps(data)

            return HttpResponse(jsonData)

        elif request.POST.get('event') == "startConfig":
            siteUser = User.objects.get(name=request.POST.get('user'))
            workSpace = Workspace.objects.get(
                name=request.POST.get('data'),
                user=siteUser,
            )

            print request.POST.get('data')

            return HttpResponse("Configuration started.")

        return HttpResponse("adsf")

    elementList = ElementTemplate.objects.all()
    template = loader.get_template('builder/index.html')
    context = RequestContext(request, {'elementList': elementList})
    return HttpResponse(template.render(context))
