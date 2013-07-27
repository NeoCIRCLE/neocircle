# coding=utf-8

from datetime import datetime
from datetime import timedelta as td
import base64
import struct
import logging

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core import signing
from django.db import models
from django.db import transaction
from django.db.models.signals import post_save, pre_delete
from django.template.defaultfilters import escape
from django.utils.translation import ugettext_lazy as _

from firewall.models import Host, Vlan
from store.api import StoreApi
from vm.models import Template
from .util import keygen
import django.conf

CLOUD_URL = django.conf.settings.CLOUD_URL

logger = logging.getLogger(__name__)
pwgen = User.objects.make_random_password


def create_user_profile(sender, instance, created, **kwargs):
    """User creation hook: create cloud details object"""
    if created:
        d = UserCloudDetails(user=instance)
        d.clean()
        d.save()

post_save.connect(create_user_profile, sender=User)


class UserCloudDetails(models.Model):
    """Cloud related details of a user."""
    user = models.OneToOneField(User, verbose_name=_('user'),
                                related_name='cloud_details')
    smb_password = models.CharField(max_length=20,
                                    verbose_name=_('Samba password'),
                                    help_text=_('Generated password for '
                                                'accessing store from '
                                                'Windows.'))
    ssh_key = models.ForeignKey('SshKey', verbose_name=_('SSH key (public)'),
                                null=True, blank=True,
                                related_name='userclouddetails_set',
                                help_text=_('Generated SSH public key for '
                                            'accessing store from Linux.'))
    ssh_private_key = models.TextField(verbose_name=_('SSH key (private)'),
                                       blank=True,
                                       help_text=_('Generated SSH private '
                                                   'key for accessing '
                                                   'store from Linux.'))
    share_quota = models.IntegerField(verbose_name=_('share quota'),
                                      default=0)
    instance_quota = models.IntegerField(verbose_name=_('instance quota'),
                                         default=20)
    disk_quota = models.IntegerField(verbose_name=_('disk quota'),
                                     default=2048,
                                     help_text=_('Disk quota in mebibytes.'))

    def reset_keys(self):
        """Deprecated. Use reset_ssh_keys instead."""
        self.reset_ssh_keys()

    def reset_ssh_keys(self):
        """Delete old SSH key pair and generate new one."""
        pri, pub = keygen()
        self.ssh_private_key = pri

        try:
            self.ssh_key.key = pub
        except AttributeError:
            self.ssh_key = SshKey(user=self.user, key=pub)
        self.ssh_key.save()
        self.ssh_key_id = self.ssh_key.id
        self.save()

    def reset_smb(self):
        """Generate new Samba password."""
        self.smb_password = pwgen()
        self.save()

    def get_weighted_instance_count(self):
        states = ['ACTIVE', 'PENDING']
        credits = [i.template.instance_type.credit
                   for i in self.user.instance_set.filter(state__in=states)]
        return sum(credits)

    def get_instance_pc(self):
        """Get what percent of the user's instance quota is in use."""
        inst_quota = self.instance_quota
        if inst_quota <= 0:
            return 100
        else:
            return 100 * self.get_weighted_instance_count() / inst_quota

    def get_weighted_share_count(self):
        credits = [s.template.instance_type.credit * s.instance_limit
                   for s in Share.objects.filter(owner=self.user)]
        return sum(credits)

    def get_share_pc(self):
        """Get what percent of the user's share quota is in use."""
        share_quota = self.share_quota
        if share_quota <= 0:
            return 100
        else:
            return 100 * self.get_weighted_share_count() / share_quota


def set_quota(sender, instance, created, **kwargs):
    try:
        if not StoreApi.userexist(instance.user.username):
            password = instance.smb_password
            quota = instance.disk_quota * 1024
            key_list = [k.key for k in instance.user.sshkey_set.all()]
            # Create user
            StoreApi.createuser(instance.user.username, password, key_list,
                                quota)
        else:
            StoreApi.set_quota(instance.user.username,
                               instance.disk_quota * 1024)
    except:
        pass
post_save.connect(set_quota, sender=UserCloudDetails)


def reset_keys(sender, instance, created, **kwargs):
    if created:
        instance.reset_smb()
        instance.reset_ssh_keys()

post_save.connect(reset_keys, sender=UserCloudDetails)


class OpenSshKeyValidator(object):
    """Validate OpenSSH keys (length and type)."""
    valid_types = ['ssh-rsa', 'ssh-dsa']

    def __init__(self, types=None):
        if types is not None:
            self.valid_types = types

    def __call__(self, value):
        try:
            value = value + ' comment'
            type, key_string, comment = value.split(None, 2)
            if type not in self.valid_types:
                raise ValidationError(_('OpenSSH key type %s is not '
                                        'supported.') % type)
            data = base64.decodestring(key_string)
            int_len = 4
            str_len = struct.unpack('>I', data[:int_len])[0]
            if not data[int_len:(int_len + str_len)] == type:
                raise
        except ValidationError:
            raise
        except:
            raise ValidationError(_('Invalid OpenSSH public key.'))


class SshKey(models.Model):
    """SSH public key (in OpenSSH format)."""
    user = models.ForeignKey(User, related_name='sshkey_set')
    key = models.TextField(verbose_name=_('SSH key'),
                           help_text=_('<a href="/info/ssh/">SSH public key '
                                       'in OpenSSH format</a> used for shell '
                                       'and store login (2048+ bit RSA '
                                       'preferred). Example: <code>ssh-rsa '
                                       'AAAAB...QtQ== john</code>.'),
                           validators=[OpenSshKeyValidator()])

    def __unicode__(self):
        try:
            keycomment = self.key.split(None, 2)[2]
        except:
            keycomment = _("unnamed")

        return u"%s (%s)" % (keycomment, self.user)

TYPES = {"LAB": {"verbose_name": _('lab'), "id": "LAB",
                 "suspend": td(hours=5), "delete": td(days=15),
                 "help_text": _('For lab or homework with short lifetime.')},
         "PROJECT": {"verbose_name": _('project'), "id": "PROJECT",
                     "suspend": td(weeks=5), "delete": td(days=366 / 2),
                     "help_text": _('For project work.')},
         "SERVER": {"verbose_name": _('server'), "id": "SERVER",
                    "suspend": td(days=365), "delete": None,
                    "help_text": _('For long-term server use.')},
         }
DEFAULT_TYPE = TYPES['LAB']
TYPES_L = sorted(TYPES.values(), key=lambda m: m["suspend"])
TYPES_C = tuple([(i[0], i[1]["verbose_name"]) for i in TYPES.items()])


class Share(models.Model):
    name = models.CharField(max_length=100, verbose_name=_('name'))
    description = models.TextField(verbose_name=_('description'))
    template = models.ForeignKey('Template', related_name='share_set')
    group = models.ForeignKey('school.Group', related_name='share_set')
    created_at = models.DateTimeField(auto_now_add=True,
                                      verbose_name=_('created at'))
    type = models.CharField(choices=TYPES_C, max_length=10)
    instance_limit = models.IntegerField(verbose_name=_('instance limit'),
                                         help_text=_('Maximal count of '
                                                     'instances launchable '
                                                     'for this share.'))
    per_user_limit = models.IntegerField(verbose_name=_('per user limit'),
                                         help_text=_('Maximal count of '
                                                     'instances launchable '
                                                     'by a single user.'))
    owner = models.ForeignKey(User, null=True, blank=True,
                              related_name='share_set')

    class Meta:
        ordering = ['group', 'template', 'owner', ]
        verbose_name = _('share')
        verbose_name_plural = _('shares')

    @classmethod
    def extend_type(cls, t):
        """Extend the share's type descriptor with absolute deletion and
           suspension time values based on the current time and intervals
           already set."""
        t['deletex'] = (datetime.now() + td(seconds=1) + t['delete']
                        if t['delete'] else None)
        t['suspendx'] = (datetime.now() + td(seconds=1) + t['suspend']
                         if t['suspend'] else None)
        return t

    def get_type(self):
        t = TYPES[self.type]
        return self.extend_type(t)

    def get_running_or_stopped(self, user=None):
        running = (Instance.objects.all().exclude(state='DONE')
                   .filter(share=self))
        if user:
            return running.filter(owner=user).count()
        else:
            return running.count()

    def get_running(self, user=None):
        running = (Instance.objects.all().exclude(state='DONE')
                   .exclude(state='STOPPED').filter(share=self))
        if user:
            return running.filter(owner=user).count()
        else:
            return running.count()

    def get_instance_pc(self):
        return float(self.get_running()) / self.instance_limit * 100

    def __unicode__(self):
        return u"%(group)s: %(tpl)s %(owner)s" % {
            'group': self.group, 'tpl': self.template, 'owner': self.owner}

    def get_used_quota(self):
        return self.template.get_credits_per_instance() * self.instance_limit
