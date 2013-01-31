# Create your views here.
from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from store.api import StoreApi
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
import os
import json

@login_required
def index(request):
    user = request.user.username
    try:
        details = request.user.userclouddetails_set.all()[0]
        password = details.smb_password
        key_list = []
        for key in request.user.sshkey_set.all():
            key_list.append(key.key)
    except:
        return HttpResponse('Can not acces to django database!', status_code=404)
    if StoreApi.userexist(user) != True:
        #Create user
        if not StoreApi.createuser(user,password,key_list):
            return HttpResponse('User does not exist on store! And could not create!')
    #UpdateAuthorizationInfo
    try:
        auth=request.POST['auth']
        if not StoreApi.updateauthorizationinfo(user,password,key_list):
           return HttpResponse('Can not update authorization information!')
    except:
        pass
    #Download handler
    try:
        dl = request.POST['dl']
        return redirect(StoreApi.requestdownload(user,dl))
    except:
        pass
    #Upload handler
    try:
        ul = request.POST['ul']
        url = StoreApi.requestupload(user,ul)
        return render_to_response('store/upload.html', RequestContext(request,{'URL' : url}))
    except:
        pass
    #Remove handler
    try:
        rm = request.POST['rm']
        succes = StoreApi.requestremove(user,rm)
    except:
        pass
    #Remove handler
    try:
        path = request.POST['path']
        new = request.POST['new']
        succes = StoreApi.requestnewfolder(user,path+'/'+new)
    except:
        pass
    #Simple file list
    path = '/'
    try:
        path = request.POST['path']
    except:
        pass
    #Normalize path (Need double dirname /folder/ -> /folder -> /
    backpath = os.path.normpath(os.path.dirname(os.path.dirname(path)))
    file_list = StoreApi.listfolder(user,path)
    return render_to_response('store/list.html', RequestContext(request, {'file_list': file_list, 'path' : path, 'backpath' : backpath, 'username' : user}))

@login_required
def ajax_listfolder(request):
    user = request.user.username
    try:
        details = request.user.userclouddetails_set.all()[0]
        password = details.smb_password
        key_list = []
        for key in request.user.sshkey_set.all():
            key_list.append(key.key)
    except:
        return HttpResponse('Can not acces to django database!', status_code=404)
    if StoreApi.userexist(user) != True:
        #Create user
        if not StoreApi.createuser(user,password,key_list):
            return HttpResponse('User does not exist on store! And could not create!', status_code=404)
    path = '/'
    try:
        path = request.POST['path']
    except:
        pass
    #Normalize path (Need double dirname /folder/ -> /folder -> /
    backpath = os.path.normpath(os.path.dirname(os.path.dirname(path)))
    file_list = StoreApi.listfolder(user,path)
    return HttpResponse(json.dumps(file_list))

@login_required
def ajax_download(request):
    user = request.user.username
    try:
        details = request.user.userclouddetails_set.all()[0]
        password = details.smb_password
        key_list = []
        for key in request.user.sshkey_set.all():
            key_list.append(key.key)
    except:
        return HttpResponse('Can not acces to django database!', status_code=404)
    if StoreApi.userexist(user) != True:
        if not StoreApi.createuser(user,password,key_list):
            return HttpResponse('User does not exist on store! And could not create!', status_code=404)
    try:
        dl = request.POST['dl']
        return HttpResponse(json.dumps({'url':StoreApi.requestdownload(user,dl)}))
    except:
        pass
    return HttpResponse('File not found!', status_code=404)

@login_required
def ajax_delete(request):
    user = request.user.username
    try:
        details = request.user.userclouddetails_set.all()[0]
        password = details.smb_password
        key_list = []
        for key in request.user.sshkey_set.all():
            key_list.append(key.key)
    except:
        return HttpResponse('Can not acces to django database!', status_code=404)
    if StoreApi.userexist(user) != True:
        if not StoreApi.createuser(user,password,key_list):
            return HttpResponse('User does not exist on store! And could not create!', status_code=404)
    try:
        rm = request.POST['rm']
        return HttpResponse(json.dumps({'success':StoreApi.requestremove(user,rm)}))
    except:
        pass
    return HttpResponse('File not found!', status_code=404)

@login_required
def toplist(request):
    user = request.user.username
    path = backpath = '/'
    file_list = StoreApi.toplist(user)
    return render_to_response('store/list.html', RequestContext(request, {'file_list': file_list, 'path' : path, 'backpath' : backpath, 'username' : user}))

def logout(request):
        auth.logout(request)
        return redirect('/')
