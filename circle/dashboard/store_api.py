from os.path import splitext
import json
import logging
from urlparse import urljoin
from datetime import datetime

from django.http import Http404
from django.conf import settings
from requests import get, post, codes
from sizefield.utils import filesizeformat

logger = logging.getLogger(__name__)


class StoreApiException(Exception):
    pass


class NotOkException(StoreApiException):
    def __init__(self, status, *args, **kwargs):
        self.status = status
        super(NotOkException, self).__init__(*args, **kwargs)


class NoStoreException(StoreApiException):
    pass


class Store(object):

    def __init__(self, user, default_timeout=0.5):
        self.request_args = {'verify': settings.STORE_VERIFY_SSL}
        if settings.STORE_SSL_AUTH:
            self.request_args['cert'] = (settings.STORE_CLIENT_CERT,
                                         settings.STORE_CLIENT_KEY)
        if settings.STORE_BASIC_AUTH:
            self.request_args['auth'] = (settings.STORE_CLIENT_USER,
                                         settings.STORE_CLIENT_PASSWORD)
        self.username = "u-%d" % user.pk
        self.default_timeout = default_timeout
        self.store_url = settings.STORE_URL
        if not self.store_url:
            raise NoStoreException

    def _request(self, url, method=get, timeout=None,
                 raise_status_code=True, **kwargs):
        url = urljoin(self.store_url, url)
        if timeout is None:
            timeout = self.default_timeout
        payload = json.dumps(kwargs)
        try:
            headers = {'content-type': 'application/json'}
            response = method(url, data=payload, headers=headers,
                              timeout=timeout, **self.request_args)
        except Exception:
            logger.exception("Error in store %s loading %s",
                             unicode(method), url)
            raise
        else:
            if raise_status_code and response.status_code != codes.ok:
                if response.status_code == 404:
                    raise Http404()
                else:
                    raise NotOkException(response.status_code)
            return response

    def _request_cmd(self, cmd, **kwargs):
        return self._request(self.username, post, CMD=cmd, **kwargs)

    def list(self, path, process=True):
        r = self._request_cmd("LIST", PATH=path)
        result = r.json()
        if process:
            return self._process_list(result)
        else:
            return result

    def toplist(self, process=True):
        r = self._request_cmd("TOPLIST")
        result = r.json()
        if process:
            return self._process_list(result)
        else:
            return result

    def request_download(self, path):
            r = self._request_cmd("DOWNLOAD", PATH=path, timeout=5)
            return r.json()['LINK']

    def request_upload(self, path):
            r = self._request_cmd("UPLOAD", PATH=path)
            return r.json()['LINK']

    def remove(self, path):
        self._request_cmd("REMOVE", PATH=path)

    def new_folder(self, path):
        self._request_cmd("NEW_FOLDER", PATH=path)

    def rename(self, old_path, new_name):
        self._request_cmd("RENAME", PATH=old_path, NEW_NAME=new_name)

    def get_quota(self):  # no CMD? :o
        r = self._request(self.username)
        return r.json()

    def set_quota(self, quota):
        self._request(self.username + "/quota/", post, QUOTA=quota)

    def user_exist(self):
        try:
            self._request(self.username)
            return True
        except NotOkException:
            return False

    def create_user(self, password, keys, quota):
        self._request("/new/" + self.username, SMBPASSWD=password, KEYS=keys,
                      QUOTA=quota)

    @staticmethod
    def _process_list(content):
        for d in content:
            d['human_readable_date'] = datetime.utcfromtimestamp(float(
                d['MTIME']))
            delta = (datetime.utcnow() -
                     d['human_readable_date']).total_seconds()
            d['is_new'] = 0 < delta < 5
            d['human_readable_size'] = (
                "directory" if d['TYPE'] == "D" else
                filesizeformat(float(d['SIZE'])))

            if d['DIR'] == ".":
                d['directory'] = "/"
            else:
                d['directory'] = "/" + d['DIR'] + "/"

            d['path'] = d['directory']
            d['path'] += d['NAME']
            if d['TYPE'] == "D":
                d['path'] += "/"

            d['ext'] = splitext(d['path'])[1]
            d['icon'] = ("folder-open" if not d['ext']
                         else file_icons.get(d['ext'], "file-o"))

        return sorted(content, key=lambda k: k['TYPE'])


file_icons = {
    '.txt': "file-text-o",
    '.pdf': "file-pdf-o",

    '.jpg': "file-image-o",
    '.jpeg': "file-image-o",
    '.png': "file-image-o",
    '.gif': "file-image-o",

    '.avi': "file-video-o",
    '.mkv': "file-video-o",
    '.mp4': "file-video-o",
    '.mov': "file-video-o",

    '.mp3': "file-sound-o",
    '.flac': "file-sound-o",
    '.wma': "file-sound-o",

    '.pptx': "file-powerpoint-o",
    '.ppt': "file-powerpoint-o",
    '.doc': "file-word-o",
    '.docx': "file-word-o",
    '.xlsx': "file-excel-o",
    '.xls': "file-excel-o",

    '.rar': "file-archive-o",
    '.zip': "file-archive-o",
    '.7z': "file-archive-o",
    '.tar': "file-archive-o",
    '.gz': "file-archive-o",

    '.py': "file-code-o",
    '.html': "file-code-o",
    '.js': "file-code-o",
    '.css': "file-code-o",
    '.c': "file-code-o",
    '.cpp': "file-code-o",
    '.h': "file-code-o",
    '.sh': "file-code-o",
}
