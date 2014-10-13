from __future__ import absolute_import

from hashlib import sha1
import logging
import M2Crypto

from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User

from dashboard.models import Profile

from .voms_helper import VOMS

logger = logging.getLogger(__name__)


# https://github.com/IFCA/keystone-voms/blob/stable/icehouse/keystone_voms/core.py
# TODO
class VomsError(Exception):
    """Voms credential management error"""

    errors = {
        0: ('none', None),
        1: ('nosocket', 'Socket problem'),
        2: ('noident', 'Cannot identify itself (certificate problem)'),
        3: ('comm', 'Server problem'),
        4: ('param', 'Wrong parameters'),
        5: ('noext', 'VOMS extension missing'),
        6: ('noinit', 'Initialization error'),
        7: ('time', 'Error in time checking'),
        8: ('idcheck', 'User data in extension different from the real'),
        9: ('extrainfo', 'VO name and URI missing'),
        10: ('format', 'Wrong data format'),
        11: ('nodata', 'Empty extension'),
        12: ('parse', 'Parse error'),
        13: ('dir', 'Directory error'),
        14: ('sign', 'Signature error'),
        15: ('server', 'Unidentifiable VOMS server'),
        16: ('mem', 'Memory problems'),
        17: ('verify', 'Generic verification error'),
        18: ('type', 'Returned data of unknown type'),
        19: ('order', 'Ordering different than required'),
        20: ('servercode', 'Error from the server'),
        21: ('notavail', 'Method not available'),
    }

    def __init__(self, value):
        self.code, self.message = self.errors.get(
            value, ('oops', 'Unknown error %d' % value))

    def __str__(self):
        return self.message


class VomsBackend(object):
    # https://github.com/IFCA/keystone-voms/blob/stable/icehouse
    # /keystone_voms/core.py
    # TODO
    @staticmethod
    def _get_cert_chain(cert, chain):
        """Return certificate and chain from the ssl info in M2Crypto format"""
        cert_out = M2Crypto.X509.load_cert_string(cert)
        chain_out = M2Crypto.X509.X509_Stack()
        for c in chain:
            aux = M2Crypto.X509.load_cert_string(c)
            if aux.check_ca():
                continue  # Don't include CA certs
            chain_out.push(aux)
        return cert_out, chain_out

    # https://github.com/IFCA/keystone-voms/blob/stable/icehouse
    # /keystone_voms/core.py
    # TODO
    def _get_voms_info(self, cert, chain):
        """Extract voms info from ssl_info and return dict with it."""

        try:
            cert, chain = self._get_cert_chain(cert, chain)
        except M2Crypto.X509.X509Error:
            raise
        with VOMS('/etc/grid-security/vomsdir/',
                  '/etc/grid-security/certificates/',
                  'libvomsapi.so.1') as v:
            voms_data = v.retrieve(cert, chain)
            if not voms_data:
                raise VomsError(v.error.value)

            d = {}
            for attr in ('user', 'userca', 'server', 'serverca',
                         'voname',  'uri', 'version', 'serial',
                         ('not_before', 'date1'), ('not_after', 'date2')):
                if isinstance(attr, basestring):
                    d[attr] = getattr(voms_data, attr)
                else:
                    d[attr[0]] = getattr(voms_data, attr[1])

            d["fqans"] = []
            for fqan in iter(voms_data.fqan):
                if fqan is None:
                    break
                d["fqans"].append(fqan)

        return d

    def authenticate(self, request):
        cert = request.environ.get('SSL_CLIENT_CERT')
        chain = []
        for k, v in request.environ.iteritems():
            if k.startswith('SSL_CLIENT_CERT_CHAIN_'):
                chain.append(v)

        if not cert or not chain:
            logger.debug('missing cert(%s) or chain(%s)', cert, chain)
            return None

        cert = cert.replace('\t', '\n')

        try:
            voms_info = self._get_voms_info(cert, chain)
        except VomsError as e:
            logger.info('VomsError: %s', str(e))
            return None
        except:
            logger.exception('Unhandled error: ')
            return None

        dn = voms_info['user']
        username = sha1(dn).hexdigest()[:30]
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            cn = dn.split('/')[-1].lstrip('CN=')
            first_name, last_name = cn.split(' ', 2)
            user = User(username=username, password='',
                        first_name=first_name, last_name=last_name)
            user.save()
            profile, created = Profile.objects.get_or_create(user=user)
            profile.org_id = dn
            profile.save()
            logger.info(u'new voms user: %s (%s)', user, dn)

        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


# https://github.com/kimvais/django-ssl-client-auth/blob/master/django_ssl_auth/base.py
class VomsMiddleware(object):
    def process_request(self, request):
        if not hasattr(request, 'user') or request.user.is_authenticated():
            return
        user = authenticate(request=request)
        if user is None or not user.is_authenticated():
            return
        logger.info("VomsMiddleware login: %s", repr(user))
        login(request, user)
