from django.db import models
from django.http import Http404
import json, requests, time
from cloud.settings import store_settings as settings

# Create your models here.
#TODO Handle exceptions locally
class StoreApi:
#    store_url = 'https://store.cloud.ik.bme.hu'
#    store_url = 'http://store.cloud.ik.bme.hu:8080'
#    store_client_cert = '/opt/webadmin/cloud/client.crt'
#    store_client_key = ''/opt/webadmin/cloud/client.key
#    store_user = 'admin'
#    store_password = 'IQu8Eice'
#    ssl_auth = True
#    verify_ssl = False
    @staticmethod
    def get_host():
        return settings['store_host']
    @staticmethod
    def post_request(url, payload):
        headers = {'content-type': 'application/json'}
        if settings['ssl_auth'] == 'True' and settings['basic_auth'] == 'True':
            r = requests.post(url, data=payload, headers=headers,  \
            verify = settings['verify_ssl']=='True', \
            cert=(settings['store_client_cert'], settings['store_client_key']), \
            auth=(settings['store_client_user'], settings['store_client_pass'])
            )
        elif settings['ssl_auth'] == 'True':
            r = requests.post(url, data=payload, headers=headers,  \
            verify = settings['verify_ssl']=='True', \
            cert=(settings['store_client_cert'], settings['store_client_key']) \
            )
        elif settings['basic_auth'] == 'True':
            r = requests.post(url, data=payload, headers=headers,  \
            verify = settings['verify_ssl']=='True', \
            auth=(settings['store_client_user'], settings['store_client_pass']) \
            )
        else:
            r = requests.post(url, data=payload, headers=headers,  \
            verify = settings['verify_ssl']=='True' \
            )
        return r
    @staticmethod
    def get_request(url):
        headers = {'content-type': 'application/json'}
        if settings['ssl_auth'] == 'True' and settings['basic_auth'] == 'True':
            r = requests.get(url, headers=headers,  \
            verify = settings['verify_ssl']=='True', \
            cert=(settings['store_client_cert'], settings['store_client_key']), \
            auth=(settings['store_client_user'], settings['store_client_pass'])
            )
        elif settings['ssl_auth'] == 'True':
            r = requests.get(url, headers=headers,  \
            verify = settings['verify_ssl']=='True', \
            cert=(settings['store_client_cert'], settings['store_client_key']) \
            )
        elif settings['basic_auth'] == 'True':
            r = requests.get(url, headers=headers,  \
            verify = settings['verify_ssl']=='True', \
            auth=(settings['store_client_user'], settings['store_client_pass']) \
            )
        else:
            r = requests.get(url, headers=headers,  \
            verify = settings['verify_ssl']=='True' \
            )
        return r
    @staticmethod
    def listfolder(neptun, path):
        url = settings['store_url']+'/'+neptun
        payload = json.dumps({ 'CMD' : 'LIST', 'PATH' : path })
        r = StoreApi.post_request(url, payload)
        if r.status_code == requests.codes.ok:
            tupplelist = json.loads(r.content)
            for item in tupplelist:
                item['MTIME'] = time.ctime(item['MTIME'])
            return tupplelist
        else:
            raise Http404
    @staticmethod
    def toplist(neptun):
        url = settings['store_url']+'/'+neptun
        payload = json.dumps({ 'CMD' : 'TOPLIST'})
        r = StoreApi.post_request(url, payload)
        if r.status_code == requests.codes.ok:
            tupplelist = json.loads(r.content)
            for item in tupplelist:
                item['MTIME'] = time.ctime(item['MTIME'])
            return tupplelist
        else:
            raise Http404
    @staticmethod
    def requestdownload(neptun, path):
        url = settings['store_url']+'/'+neptun
        payload = json.dumps({ 'CMD' : 'DOWNLOAD', 'PATH' : path })
        r = StoreApi.post_request(url, payload)
        response = json.loads(r.content)
        return response['LINK']
    @staticmethod
    def requestupload(neptun, path):
        url = settings['store_url']+'/'+neptun
        payload = json.dumps({ 'CMD' : 'UPLOAD', 'PATH' : path })
        headers = {'content-type': 'application/json'}
        r = StoreApi.post_request(url, payload)
        response = json.loads(r.content)
        if r.status_code == requests.codes.ok:
            return response['LINK']
        else:
            raise Http404
    @staticmethod
    def requestremove(neptun, path):
        url = settings['store_url']+'/'+neptun
        payload = json.dumps({ 'CMD' : 'REMOVE', 'PATH' : path })
        headers = {'content-type': 'application/json'}
        r = StoreApi.post_request(url, payload)
        if r.status_code == requests.codes.ok:
            return True
        else:
            return False
    @staticmethod
    def requestnewfolder(neptun, path):
        url = settings['store_url']+'/'+neptun
        payload = json.dumps({ 'CMD' : 'NEW_FOLDER', 'PATH' : path })
        headers = {'content-type': 'application/json'}
        r = StoreApi.post_request(url, payload)
        if r.status_code == requests.codes.ok:
            return True
        else:
            return False
    @staticmethod
    def requestquota(neptun):
        url = settings['store_url']+'/'+neptun
        r = StoreApi.get_request(url)
        if r.status_code == requests.codes.ok:
            return json.loads(r.content)
        else:
            return False
    @staticmethod
    def userexist(neptun):
        url = settings['store_url']+'/'+neptun
        r = StoreApi.get_request(url)
        if r.status_code == requests.codes.ok:
            return True
        else:
            return False
    @staticmethod
    def createuser(neptun, password, key_list):
        url = settings['store_url']+'/new/'+neptun
        payload = json.dumps({ 'SMBPASSWD' : password, 'KEYS' : key_list })
        r = StoreApi.post_request(url, payload)
        if r.status_code == requests.codes.ok:
            return True
        else:
            return False
    @staticmethod
    def updateauthorizationinfo(neptun, password, key_list):
        url = settings['store_url']+'/set/'+neptun
        payload = json.dumps({ 'SMBPASSWD' : password, 'KEYS' : key_list })
        r = StoreApi.post_request(url, payload)
        if r.status_code == requests.codes.ok:
            return True
        else:
            return False



