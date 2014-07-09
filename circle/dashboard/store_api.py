from django.http import Http404
import json
import requests
import django.conf

from datetime import datetime
from sizefield.utils import filesizeformat

settings = django.conf.settings.STORE_SETTINGS


class Mock(object):
    pass


def get_host():
    return settings['store_url']


def post_request(url, payload):
    try:
        headers = {'content-type': 'application/json'}
        if settings['ssl_auth'] == 'True' and settings['basic_auth'] == 'True':
            r = requests.post(url, data=payload, headers=headers,
                              verify=settings['verify_ssl'] == 'True',
                              cert=(settings['store_client_cert'],
                                    settings['store_client_key']),
                              auth=(settings['store_client_user'],
                                    settings['store_client_pass'])
                              )
        elif settings['ssl_auth'] == 'True':
            r = requests.post(url, data=payload, headers=headers,
                              verify=settings['verify_ssl'] == 'True',
                              cert=(settings['store_client_cert'],
                                    settings['store_client_key'])
                              )
        elif settings['basic_auth'] == 'True':
            r = requests.post(url, data=payload, headers=headers,
                              verify=settings['verify_ssl'] == 'True',
                              auth=(settings['store_client_user'],
                                    settings['store_client_pass'])
                              )
        else:
            r = requests.post(url, data=payload, headers=headers,
                              verify=settings['verify_ssl'] == 'True'
                              )
        return r
    except:
        dummy = Mock()
        setattr(dummy, "status_code", 200)
        setattr(dummy, "content", "[]")
        return dummy


def get_request(url):
    try:
        headers = {'content-type': 'application/json'}
        if settings['ssl_auth'] == 'True' and settings['basic_auth'] == 'True':
            r = requests.get(
                url,
                headers=headers,
                verify=settings['verify_ssl'] == 'True',
                cert=(
                    settings['store_client_cert'],
                    settings['store_client_key']),
                auth=(
                    settings['store_client_user'],
                    settings['store_client_pass']))
        elif settings['ssl_auth'] == 'True':
            r = requests.get(
                url,
                headers=headers,
                verify=settings['verify_ssl'] == 'True',
                cert=(
                    settings['store_client_cert'],
                    settings['store_client_key']))
        elif settings['basic_auth'] == 'True':
            r = requests.get(
                url,
                headers=headers,
                verify=settings['verify_ssl'] == 'True',
                auth=(
                    settings['store_client_user'],
                    settings['store_client_pass']))
        else:
            r = requests.get(url, headers=headers,
                             verify=settings['verify_ssl'] == 'True'
                             )
            return r
    except:
        dummy = Mock()
        setattr(dummy, "status_code", 200)
        setattr(dummy, "content", "[]")
        return dummy


def listfolder(neptun, path):
    url = settings['store_url']+'/'+neptun
    payload = json.dumps({'CMD': 'LIST', 'PATH': path})
    r = post_request(url, payload)
    if r.status_code == requests.codes.ok:
        tupplelist = json.loads(r.content)
        return tupplelist
    else:
        raise Http404


def toplist(neptun):
    url = settings['store_url']+'/'+neptun
    payload = json.dumps({'CMD': 'TOPLIST'})
    r = post_request(url, payload)
    if r.status_code == requests.codes.ok:
        tupplelist = json.loads(r.content)
        return tupplelist
    else:
        raise Http404


def requestdownload(neptun, path):
    url = settings['store_url']+'/'+neptun
    payload = json.dumps({'CMD': 'DOWNLOAD', 'PATH': path})
    r = post_request(url, payload)
    response = json.loads(r.content)
    return response['LINK']


def requestupload(neptun, path):
    url = settings['store_url']+'/'+neptun
    payload = json.dumps({'CMD': 'UPLOAD', 'PATH': path})
    r = post_request(url, payload)
    response = json.loads(r.content)
    if r.status_code == requests.codes.ok:
        return response['LINK']
    else:
        raise Http404


def requestremove(neptun, path):
    url = settings['store_url']+'/'+neptun
    payload = json.dumps({'CMD': 'REMOVE', 'PATH': path})
    r = post_request(url, payload)
    if r.status_code == requests.codes.ok:
        return True
    else:
        return False


def requestnewfolder(neptun, path):
    url = settings['store_url']+'/'+neptun
    payload = json.dumps({'CMD': 'NEW_FOLDER', 'PATH': path})
    r = post_request(url, payload)
    if r.status_code == requests.codes.ok:
        return True
    else:
        return False


def requestrename(neptun, old_path, new_name):
    url = settings['store_url']+'/'+neptun
    payload = json.dumps(
        {'CMD': 'RENAME', 'NEW_NAME': new_name, 'PATH': old_path})
    r = post_request(url, payload)
    if r.status_code == requests.codes.ok:
        return True
    else:
        return False


def requestquota(neptun):
    url = settings['store_url']+'/'+neptun
    r = get_request(url)
    if r.status_code == requests.codes.ok:
        return json.loads(r.content)
    else:
        return False


def set_quota(neptun, quota):
    url = settings['store_url']+'/quota/'+neptun
    payload = json.dumps({'QUOTA': quota})
    r = post_request(url, payload)
    if r.status_code == requests.codes.ok:
        return True
    else:
        return False


def userexist(neptun):
    url = settings['store_url']+'/'+neptun
    r = get_request(url)
    if r.status_code == requests.codes.ok:
        return True
    else:
        return False


def createuser(neptun, password, key_list, quota):
    url = settings['store_url']+'/new/'+neptun
    payload = json.dumps(
        {'SMBPASSWD': password, 'KEYS': key_list, 'QUOTA': quota})
    r = post_request(url, payload)
    if r.status_code == requests.codes.ok:
        return True
    else:
        return False


def updateauthorizationinfo(neptun, password, key_list):
    url = settings['store_url']+'/set/'+neptun
    payload = json.dumps({'SMBPASSWD': password, 'KEYS': key_list})
    r = post_request(url, payload)
    if r.status_code == requests.codes.ok:
        return True
    else:
        return False


def process_list(content):
    for d in content:
        d['human_readable_date'] = datetime.utcfromtimestamp(float(
            d['MTIME']))
        delta = (datetime.utcnow() - d['human_readable_date']).total_seconds()
        d['is_new'] = delta < 5 and delta > 0
        d['human_readable_size'] = (
            "directory" if d['TYPE'] == "D" else
            filesizeformat(float(d['SIZE'])))

        d['path'] = d['DIR']
        if len(d['path']) == 1 and d['path'][0] == ".":
            d['path'] = "/"
        else:
            d['path'] = "/" + d['path'] + "/"

        d['path'] += d['NAME']
        if d['TYPE'] == "D":
            d['path'] += "/"

    return sorted(content, key=lambda k: k['TYPE'])
