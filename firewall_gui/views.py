from django.http import HttpResponse
from django.shortcuts import render

from firewall.fw import *
from firewall.models import *

def index(request):
    return HttpResponse("Ez itt a bd tuzfaladminja.")

def list_rules(request):
    rules = Rule.objects.all()
    return render(request, 'rule/list.html', {
        'rules': rules,
        })

