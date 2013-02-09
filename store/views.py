# Create your views here.
from django.core.context_processors import csrf
from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from store.api import StoreApi
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
import os
import json
import base64

def estabilish_store_user(user):
    try:
        details = request.user.userclouddetails_set.all()[0]
        password = details.smb_password
        quota = details.disk_quota * 1024
        key_list = []
        for key in request.user.sshkey_set.all():
            key_list.append(key.key)
    except:
        return HttpResponse('Can not acces to django database!', status_code=404)
        #Create user
        if not StoreApi.createuser(user, password, key_list, str(quota)):
            return HttpResponse('User does not exist on store! And could not create!')

@login_required
def index(request):
    user = request.user.username
    if StoreApi.userexist(user) != True:
        estabilish_store_user(user)
    #UpdateAuthorizationInfo
    try:
        auth=request.POST['auth']
        try:
            details = request.user.userclouddetails_set.all()[0]
            password = details.smb_password
            key_list = []
            for key in request.user.sshkey_set.all():
                key_list.append(key.key)
        except:
            return HttpResponse('Can not acces to django database!', status_code=404)
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
    quota = StoreApi.requestquota(user)
    return render_to_response('store/list.html', RequestContext(request, {'file_list': file_list, 'path' : path, 'backpath' : backpath, 'username' : user, 'quota' : quota}))

@login_required
def ajax_listfolder(request):
    user = request.user.username
    if StoreApi.userexist(user) != True:
        estabilish_store_user(user)
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
def ajax_quota(request):
    user = request.user.username
    if StoreApi.userexist(user) != True:
        estabilish_store_user(user)
    return HttpResponse(json.dumps(StoreApi.requestquota(user)))
    #return HttpResponse(json.dumps({'Used':20,'Soft':160,'Hard':200}))

@login_required
def ajax_download(request):
    user = request.user.username
    try:
        dl = request.POST['dl']
        return HttpResponse(json.dumps({'url':StoreApi.requestdownload(user,dl)}))
    except:
        pass
    return HttpResponse('File not found!', status_code=404)

@login_required
def ajax_upload(request):
    user = request.user.username
    try:
        ul = request.POST['ul']
        url = StoreApi.requestupload(user,ul)
        return HttpResponse(json.dumps({'url':url}))
    except:
        pass
    return HttpResponse('Error!', status_code=404)

@login_required
def ajax_delete(request):
    user = request.user.username
    try:
        rm = request.POST['rm']
        return HttpResponse(json.dumps({'success':StoreApi.requestremove(user,rm)}))
    except:
        pass
    return HttpResponse('File not found!', status_code=404)

@login_required
def ajax_new_folder(request):
    user = request.user.username
    try:
        path = request.POST['path']
        new = request.POST['new']
        success = StoreApi.requestnewfolder(user,path+'/'+new)
        return HttpResponse(json.dumps({'success':success}))
    except:
        pass
    return HttpResponse('Error!', status_code=404)

@login_required
def ajax_rename(request):
    user = request.user.username
    try:
        path = request.POST['path']
        new = request.POST['new']
        success = StoreApi.requestrename(user,path,new)
        return HttpResponse(json.dumps({'success':success}))
    except:
        pass
    return HttpResponse('Error!', status_code=404)

@login_required
def toplist(request):
    user = request.user.username
    path = backpath = '/'
    file_list = StoreApi.toplist(user)
    return render_to_response('store/list.html', RequestContext(request, {'file_list': file_list, 'path' : path, 'backpath' : backpath, 'username' : user}))

@login_required
def gui(request):
    user = request.user.username
    if request.method == 'GET':
        return render_to_response('store/gui.html',  RequestContext(request, {'username' : user, 'host' : StoreApi.get_host()}))
    elif request.method == 'POST':
        try:
            details = request.user.userclouddetails_set.all()[0]
            password = details.smb_password
            key_list = []
            for key in request.user.sshkey_set.all():
                key_list.append(key.key)
        except:
            return HttpResponse('Can not acces to django database!', status_code=404)
        try:
            lab_key_decoded = base64.b64decode(request.POST['KEY'])
            key_list.append(lab_key_decoded)
        except:
            if StoreApi.updateauthorizationinfo(user, password, key_list):
                return HttpResponse('Keys resetted succesfully!')
            else:
                return HttpResponse('Can not update authorization information!')
        if StoreApi.updateauthorizationinfo(user, password, key_list):
            return HttpResponse('https://cloud.ik.bme.hu/?neptun='+user+"&"+"host="+StoreApi.get_host())
        else:
            return HttpResponse('Can not update authorization information!')
    else:
        return HttpResponse('Method not found!', status_code=404)

def logout(request):
        auth.logout(request)
        return redirect('/')
