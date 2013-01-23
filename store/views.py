# Create your views here.
from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from store.models import StoreApi
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
import os

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
        return HttpResponse('Can not acces to django database!')
    if StoreApi.UserExist(user) != True:
        #Create user
        if StoreApi.CreateUser(user,password,key_list):
            pass
        else:
            return HttpResponse('User does not exist on store! And could not create!')
    #UpdateAuthorizationInfo
    try:
        auth=request.POST['auth']
        result='ures'
        result=UpdateAuthorizationInfo(user,password,key_list)
    except:
        return HttpResponse('Error: '+result)
    #Download handler
    try:
        dl = request.POST['dl']
        return redirect(StoreApi.RequestDownload(user,dl))
    except:
        pass
    #Upload handler
    try:
        ul = request.POST['ul']
        url = StoreApi.RequestUpload(user,ul)
        return render_to_response('store/upload.html', RequestContext(request,{'URL' : url}))
    except:
        pass
    #Remove handler
    try:
        rm = request.POST['rm']
        succes = StoreApi.RequestRemove(user,rm)
    except:
        pass
    #Remove handler
    try:
        path = request.POST['path']
        new = request.POST['new']
        succes = StoreApi.RequestNewFolder(user,path+'/'+new)
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
    file_list = StoreApi.ListFolder(user,path)
    return render_to_response('store/list.html', RequestContext(request,{'file_list': file_list, 'path' : path, 'backpath' : backpath, 'username' : user}))

def logout(request):
        auth.logout(request)
        return redirect('/')
