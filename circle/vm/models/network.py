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

from __future__ import absolute_import, unicode_literals

from logging import getLogger
from netaddr import EUI, mac_unix

from django.db.models import Model, ForeignKey, BooleanField, CharField
from django.utils.translation import ugettext_lazy as _, ugettext_noop

from common.models import create_readable
from firewall.models import Vlan, Host
from network.models import Vxlan
from ..tasks import net_tasks

logger = getLogger(__name__)


class InterfaceTemplate(Model):

    """Network interface template for an instance template.

    If the interface is managed, a host will be created for it.
    Use with Vxlan is never managed.
    """
    vlan = ForeignKey(Vlan, blank=True, null=True,
                      verbose_name=_('vlan'),
                      help_text=_('Network the interface belongs to.'))
    vxlan = ForeignKey(Vxlan, blank=True, null=True,
                       verbose_name=_('vxlan'),
                       help_text=_('Virtual network the interface '
                                   'belongs to.'))
    managed = BooleanField(verbose_name=_('managed'), default=True,
                           help_text=_('If a firewall host (i.e. IP address '
                                       'association) should be generated.'))
    template = ForeignKey('InstanceTemplate', verbose_name=_('template'),
                          related_name='interface_set',
                          help_text=_('Template the interface '
                                      'template belongs to.'))

    class Meta:
        app_label = 'vm'
        db_table = 'vm_interfacetemplate'
        permissions = ()
        verbose_name = _('interface template')
        verbose_name_plural = _('interface templates')

    def __unicode__(self):
        if self.vlan:
            return "%s - %s - %s" % (self.template, self.vlan, self.managed)
        else:  # vxlan
            return "%s - %s - %s" % (self.template, self.vxlan, False)


class Interface(Model):

    """Network interface for an instance.
    """
    MODEL_TYPES = (('virtio', 'virtio'), ('ne2k_pci', 'ne2k_pci'),
                   ('pcnet', 'pcnet'), ('rtl8139', 'rtl8139'),
                   ('e1000', 'e1000'))
    vlan = ForeignKey(Vlan, blank=True, null=True,
                      verbose_name=_('vlan'),
                      related_name="vm_interface")
    vxlan = ForeignKey(Vxlan, blank=True, null=True,
                       verbose_name=_('vxlan'),
                       related_name="vm_interface")
    host = ForeignKey(Host, verbose_name=_('host'),  blank=True, null=True)
    instance = ForeignKey('Instance', verbose_name=_('instance'),
                          related_name='interface_set')
    model = CharField(max_length=10, choices=MODEL_TYPES, default='virtio')

    class Meta:
        app_label = 'vm'
        db_table = 'vm_interface'
        ordering = ("-vlan__managed", )

    def __unicode__(self):
        if self.vxlan is None:
            return 'cloud-%s-%s' % (str(self.instance.id),
                                    str(self.vlan.vid))
        else:  # vxlan
            return 'cloud-%s-x%s' % (str(self.instance.id),
                                     str(self.vxlan.vni))

    @property
    def mac(self):
        try:
            return self.host.mac
        except:
            return Interface.generate_mac(
                self.instance,
                self.vlan.vid if self.vxlan is None else self.vxlan.vni,
                self.vxlan is not None
            )

    @classmethod
    def generate_mac(cls, instance, vid, is_vxlan):
        """Generate MAC address for a VM instance on a VLAN.
        """
        # MAC 02:XX:XX:XX:XX:XX
        #        \______/ |\__/
        #          VM ID  | V(X)LAN ID
        #       __________|_____
        #      /                \
        #       VXLAN: 1, VLAN: 0
        class mac_custom(mac_unix):
            word_fmt = '%.2X'
        i = instance.id & 0xffffff
        v = vid & 0xfff
        vx = 1 if is_vxlan else 0
        m = (0x02 << 40) | (i << 16) | (vx << 12) | v
        return EUI(m, dialect=mac_custom)

    def get_vmnetwork_desc(self):
        return {
            'name': self.__unicode__(),
            'bridge': ('cloud' if self.vxlan is None
                       else 'cloudx-%s' % self.vxlan.vni),
            'mac': str(self.mac),
            'ipv4': str(self.host.ipv4) if self.host is not None else None,
            'ipv6': str(self.host.ipv6) if self.host is not None else None,
            'vlan': self.vlan.vid,
            'vxlan': self.vxlan.vni if self.vxlan is not None else None,
            'model': self.model,
            'managed': self.host is not None
        }

    @classmethod
    def create(cls, instance, vlan, managed, vxlan=None,
               owner=None, base_activity=None):
        """Create a new interface for a VM instance to the specified VLAN.
        """
        if managed and vxlan is None:
            host = Host()
            host.vlan = vlan
            # TODO change Host's mac field's type to EUI in firewall
            host.mac = str(cls.generate_mac(instance, vlan.vid, False))
            host.hostname = instance.vm_name
            # Get addresses from firewall
            if base_activity is None:
                act_ctx = instance.activity(
                    code_suffix='allocating_ip',
                    readable_name=ugettext_noop("allocate IP address"),
                    user=owner)
            else:
                act_ctx = base_activity.sub_activity(
                    'allocating_ip',
                    readable_name=ugettext_noop("allocate IP address"))
            with act_ctx as act:
                addresses = vlan.get_new_address()
                host.ipv4 = addresses['ipv4']
                host.ipv6 = addresses['ipv6']
                act.result = create_readable(
                    ugettext_noop("Interface successfully created."),
                    ugettext_noop("Interface successfully created. "
                                  "New addresses: ipv4: %(ip4)s, "
                                  "ipv6: %(ip6)s, vlan: %(vlan)s."),
                    ip4=unicode(host.ipv4), ip6=unicode(host.ipv6),
                    vlan=vlan.name)
            host.owner = owner
            if vlan.network_type == 'public':
                host.shared_ip = False
                host.external_ipv4 = None
            elif vlan.network_type == 'portforward':
                host.shared_ip = True
                host.external_ipv4 = vlan.snat_ip
            host.full_clean()
            host.save()
            host.enable_net()
            from .instance import ACCESS_PROTOCOLS
            port, proto = ACCESS_PROTOCOLS[instance.access_method][1:3]
            host.add_port(proto, private=port)
        else:
            host = None

        iface = cls(vlan=vlan, vxlan=vxlan, host=host, instance=instance)
        iface.save()
        return iface

    def deploy(self):
        queue_name = self.instance.get_remote_queue_name('net', 'fast')
        return net_tasks.create.apply_async(args=[self.get_vmnetwork_desc()],
                                            queue=queue_name).get()

    def shutdown(self):
        queue_name = self.instance.get_remote_queue_name('net', 'fast')
        return net_tasks.destroy.apply_async(args=[self.get_vmnetwork_desc()],
                                             queue=queue_name).get()

    def destroy(self):
        if self.host is not None:
            self.host.delete()

    def save_as_template(self, instance_template):
        """Create a template based on this interface.
        """
        i = InterfaceTemplate(vlan=self.vlan,
                              managed=(
                                self.host is not None or
                                self.vxlan or not None),
                              template=instance_template)
        i.save()
        return i
