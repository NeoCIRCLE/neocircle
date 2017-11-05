# Copyright 2014 Budapest University of Technology and Economics (BME IK)
#
# This file is part of CIRCLE Cloud.
#
# CIRCLE is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# CIRCLE is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along
# with CIRCLE.  If not, see <http://www.gnu.org/licenses/>.
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from acl.models import AclBase
from firewall.models import Vlan
from firewall.fields import val_alfanum


class Vxlan(AclBase, models.Model):

    """
    A virtual L2 network,

    These networks are isolated by the vxlan (virtual extensible lan)
    technology, which is commonly used by managed network switches
    to partition the network, with a more scalable way opposite vlan
    technology. Usually, it used over vlan networks.

    Each vxlan network has a unique identifier (VNI), a name, and
    a server vlan network.
    """

    ACL_LEVELS = (
        ('user', _('user')),
        ('operator', _('operator')),
    )
    vni = models.IntegerField(unique=True,
                              verbose_name=_('VNI'),
                              help_text=_('VXLAN Network Identifier.'),
                              validators=[MinValueValidator(0),
                                          MaxValueValidator(2 ** 24 - 1)])
    vlan = models.ForeignKey(Vlan,
                             verbose_name=_('vlan'),
                             help_text=_('The server vlan.'))
    name = models.CharField(max_length=20,
                            unique=True,
                            verbose_name=_('Name'),
                            help_text=_('The short name of the '
                                        'virtual network.'),
                            validators=[val_alfanum])
    description = models.TextField(blank=True, verbose_name=_('description'),
                                   help_text=_(
                                       'Description of the goals and elements '
                                       'of the virtual network.'))
    comment = models.TextField(blank=True,
                               verbose_name=_('comment'),
                               help_text=_(
                                   'Notes, comments about the network'))
    created_at = models.DateTimeField(auto_now_add=True,
                                      verbose_name=_('created at'))
    owner = models.ForeignKey(User, blank=True, null=True,
                              verbose_name=_('owner'))
    modified_at = models.DateTimeField(auto_now=True,
                                       verbose_name=_('modified at'))

    class Meta:
        app_label = 'network'
        verbose_name = _("vxlan")
        verbose_name_plural = _("vxlans")
        ordering = ('vni', )

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('network.vxlan', kwargs={'vni': self.vni})
