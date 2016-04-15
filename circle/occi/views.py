from django.shortcuts import render
from django.views.generic import View
from django.http import HttpResponse


# Create your views here.
# MY VIEWS ARE SOOOO GOOD
class testView(View):
    """ This view is a big test """
    def get(self, request, *args, **kwargs):
        return HttpResponse('<!DOCTYPE html><html lang="hu"><head>'
                            '<title>TEST</title></head>'
                            '<body style="background: black; color: white'
                            '; text-align: center;"><h1>TEST</h1><p>'
                            'Csilli-villi service</p></body></html>')

class startVM(View):
    """ A test service, which starts a VM """
    def get(self, request, *args, **kwargs):
        pass
