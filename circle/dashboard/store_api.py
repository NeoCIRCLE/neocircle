from django.http import Http404
import json
import logging
import requests

from datetime import datetime
from sizefield.utils import filesizeformat

from django.conf import settings

logger = logging.getLogger(__name__)


class Mock(object):
    pass


def get_host():
    return settings.STORE_URL


def get_request_arguments():
    args = {'verify': settings.STORE_VERIFY_SSL}

    if settings.STORE_SSL_AUTH:
        args['cert'] = (settings.STORE_CLIENT_CERT, settings.STORE_CLIENT_KEY)
    if settings.STORE_BASIC_AUTH:
        args['auth'] = (settings.STORE_CLIENT_USER,
                        settings.STORE_CLIENT_PASSWORD)
    return args


def post_request(url, payload, timeout=None):
    try:
        headers = {'content-type': 'application/json'}
        r = requests.post(url, data=payload, headers=headers, timeout=timeout,
                          **get_request_arguments())
        return r
    except Exception as e:
        logger.error("Error in store POST: %s" % e)
        dummy = Mock()
        setattr(dummy, "status_code", 200)
        setattr(dummy, "content", "[]")
        return dummy


def get_request(url, timeout=None):
    try:
        headers = {'content-type': 'application/json'}
        r = requests.get(url, headers=headers, timeout=timeout,
                         **get_request_arguments())
        return r
    except Exception as e:
        logger.error("Error in store GET: %s" % e)
        dummy = Mock()
        setattr(dummy, "status_code", 200)
        setattr(dummy, "content", "[]")
        return dummy


def listfolder(neptun, path):
    url = settings.STORE_URL + '/' + neptun
    payload = json.dumps({'CMD': 'LIST', 'PATH': path})
    r = post_request(url, payload, timeout=5)
    if r.status_code == requests.codes.ok:
        tupplelist = json.loads(r.content)
        return tupplelist
    else:
        raise Http404


def toplist(neptun):
    url = settings.STORE_URL + '/' + neptun
    payload = json.dumps({'CMD': 'TOPLIST'})
    r = post_request(url, payload, timeout=2)
    if r.status_code == requests.codes.ok:
        tupplelist = json.loads(r.content)
        return tupplelist
    else:
        raise Http404


def requestdownload(neptun, path):
    url = settings.STORE_URL + '/' + neptun
    payload = json.dumps({'CMD': 'DOWNLOAD', 'PATH': path})
    r = post_request(url, payload)
    response = json.loads(r.content)
    return response['LINK']


def requestupload(neptun, path):
    url = settings.STORE_URL+'/'+neptun
    payload = json.dumps({'CMD': 'UPLOAD', 'PATH': path})
    r = post_request(url, payload)
    response = json.loads(r.content)
    print response
    if r.status_code == requests.codes.ok:
        return response['LINK']
    else:
        raise Http404


def requestremove(neptun, path):
    url = settings.STORE_URL+'/'+neptun
    payload = json.dumps({'CMD': 'REMOVE', 'PATH': path})
    r = post_request(url, payload)
    if r.status_code == requests.codes.ok:
        return True
    else:
        return False


def requestnewfolder(neptun, path):
    url = settings.STORE_URL+'/'+neptun
    payload = json.dumps({'CMD': 'NEW_FOLDER', 'PATH': path})
    r = post_request(url, payload)
    if r.status_code == requests.codes.ok:
        return True
    else:
        return False


def requestrename(neptun, old_path, new_name):
    url = settings.STORE_URL+'/'+neptun
    payload = json.dumps(
        {'CMD': 'RENAME', 'NEW_NAME': new_name, 'PATH': old_path})
    r = post_request(url, payload)
    if r.status_code == requests.codes.ok:
        return True
    else:
        return False


def requestquota(neptun):
    url = settings.STORE_URL+'/'+neptun
    r = get_request(url)
    if r.status_code == requests.codes.ok:
        return json.loads(r.content)
    else:
        return False


def set_quota(neptun, quota):
    url = settings.STORE_URL+'/quota/'+neptun
    payload = json.dumps({'QUOTA': quota})
    r = post_request(url, payload)
    if r.status_code == requests.codes.ok:
        return True
    else:
        return False


def userexist(neptun):
    url = settings.STORE_URL+'/'+neptun
    r = get_request(url, timeout=5)
    if r.status_code == requests.codes.ok:
        return True
    else:
        return False


def createuser(neptun, password, key_list, quota):
    url = settings.STORE_URL+'/new/'+neptun
    payload = json.dumps(
        {'SMBPASSWD': password, 'KEYS': key_list, 'QUOTA': quota})
    r = post_request(url, payload, timeout=5)
    if r.status_code == requests.codes.ok:
        return True
    else:
        return False


def updateauthorizationinfo(neptun, password, key_list):
    url = settings.STORE_URL+'/set/'+neptun
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

        if len(d['DIR']) == 1 and d['DIR'][0] == ".":
            d['directory'] = "/"
        else:
            d['directory'] = "/" + d['DIR'] + "/"

        d['path'] = d['directory']
        d['path'] += d['NAME']
        if d['TYPE'] == "D":
            d['path'] += "/"

    return sorted(content, key=lambda k: k['TYPE'])
