from django.db import models
from django.http import Http404
import json, requests, time
# Create your models here.
#TODO Handle exceptions locally
class StoreApi(models.Model):
#    store_url = 'https://store.cloud.ik.bme.hu'
    store_url = 'http://store.cloud.ik.bme.hu:8080'
    store_user = 'admin'
    store_password = 'IQu8Eice'
    basic_auth = True
    verify_ssl = False
    @staticmethod
    def listfolder(neptun, path):
        url = StoreApi.store_url+'/'+neptun
        payload = json.dumps({ 'CMD' : 'LIST', 'PATH' : path })
        headers = {'content-type': 'application/json'}
        if StoreApi.basic_auth:
            r = requests.post(url, data=payload, headers=headers, auth=(StoreApi.store_user, StoreApi.store_password), verify=StoreApi.verify_ssl)
        else:
            r = requests.post(url, data=payload, headers=headers)
        if r.status_code == requests.codes.ok:
            tupplelist = json.loads(r.content)
            for item in tupplelist:
                item['MTIME'] = time.ctime(item['MTIME'])
            return tupplelist
        else:
            raise Http404
    @staticmethod
    def requestdownload(neptun, path):
        url = StoreApi.store_url+'/'+neptun
        payload = json.dumps({ 'CMD' : 'DOWNLOAD', 'PATH' : path })
        headers = {'content-type': 'application/json'}
        if StoreApi.basic_auth:
            r = requests.post(url, data=payload, headers=headers, auth=(StoreApi.store_user, StoreApi.store_password), verify=StoreApi.verify_ssl)
        else:
            r = requests.post(url, data=payload, headers=headers)
        response = json.loads(r.content)
        return response['LINK']
    @staticmethod
    def requestupload(neptun, path):
        url = StoreApi.store_url+'/'+neptun
        payload = json.dumps({ 'CMD' : 'UPLOAD', 'PATH' : path })
        headers = {'content-type': 'application/json'}
        if StoreApi.basic_auth:
            r = requests.post(url, data=payload, headers=headers, auth=(StoreApi.store_user, StoreApi.store_password), verify=StoreApi.verify_ssl)
        else:
            r = requests.post(url, data=payload, headers=headers)
        response = json.loads(r.content)
        if r.status_code == requests.codes.ok:
            return response['LINK']
        else:
            raise Http404
    @staticmethod
    def requestremove(neptun, path):
        url = StoreApi.store_url+'/'+neptun
        payload = json.dumps({ 'CMD' : 'REMOVE', 'PATH' : path })
        headers = {'content-type': 'application/json'}
        if StoreApi.basic_auth:
            r = requests.post(url, data=payload, headers=headers, auth=(StoreApi.store_user, StoreApi.store_password), verify=StoreApi.verify_ssl)
        else:
            r = requests.post(url, data=payload, headers=headers)
        if r.status_code == requests.codes.ok:
            return True
        else:
            return False
    @staticmethod
    def requestnewfolder(neptun, path):
        url = StoreApi.store_url+'/'+neptun
        payload = json.dumps({ 'CMD' : 'NEW_FOLDER', 'PATH' : path })
        headers = {'content-type': 'application/json'}
        if StoreApi.basic_auth:
            r = requests.post(url, data=payload, headers=headers, auth=(StoreApi.store_user, StoreApi.store_password), verify=StoreApi.verify_ssl)
        else:
            r = requests.post(url, data=payload, headers=headers)
        if r.status_code == requests.codes.ok:
            return True
        else:
            return False
    @staticmethod
    def userexist(neptun):
        url = StoreApi.store_url+'/'+neptun
        if StoreApi.basic_auth:
            r = requests.get(url, auth=(StoreApi.store_user,StoreApi.store_password), verify=StoreApi.verify_ssl)
        else:
            r = requests.get(url)
        if r.status_code == requests.codes.ok:
            return True
        else:
            return False
    @staticmethod
    def createuser(neptun, password, key_list):
        url = StoreApi.store_url+'/new/'+neptun
        payload = json.dumps({ 'SMBPASSWD' : password, 'KEYS' : key_list })
        headers = {'content-type': 'application/json'}
        if StoreApi.basic_auth:
            r = requests.post(url, data=payload, headers=headers, auth=(StoreApi.store_user, StoreApi.store_password), verify=StoreApi.verify_ssl)
        else:
            r = requests.post(url, data=payload, headers=headers)
        if r.status_code == requests.codes.ok:
            return True
        else:
            return False
    @staticmethod
    def updateauthorizationinfo(neptun, password, key_list):
        url = StoreApi.store_url+'/set/'+neptun
        payload = json.dumps({ 'SMBPASSWD' : password, 'KEYS' : key_list })
        headers = {'content-type': 'application/json'}
        if StoreApi.basic_auth:
            r = requests.post(url, data=payload, headers=headers, auth=(StoreApi.store_user, StoreApi.store_password), verify=StoreApi.verify_ssl)
        else:
            r = requests.post(url, data=payload, headers=headers)
        if r.status_code == requests.codes.ok:
            return True
        else:
            return False



