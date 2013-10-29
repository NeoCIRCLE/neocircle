from django.views.generic.base import View
from django.http import HttpResponse
from django.core import signing
from django.shortcuts import get_object_or_404
from vm.models import Instance
from datetime import datetime


class BootUrl(View):
    def get(self, request, token):
        try:
            id = signing.loads(token, salt='activate')
        except:
            return HttpResponse("Invalid token.")
        inst = get_object_or_404(Instance, id=id)
        if inst.active_since:
            return HttpResponse("Already booted?")
        else:
            inst.active_since = datetime.now()
            inst.save()
            return HttpResponse("KTHXBYE")
