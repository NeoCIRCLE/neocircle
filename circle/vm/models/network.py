from __future__ import absolute_import, unicode_literals

from logging import getLogger
from netaddr import EUI, mac_unix

from django.db.models import Model, ForeignKey, BooleanField
from django.utils.translation import ugettext_lazy as _

from firewall.models import Vlan, Host
from ..tasks import net_tasks

logger = getLogger(__name__)


class InterfaceTemplate(Model):

    """Network interface template for an instance template.

    If the interface is managed, a host will be created for it.
    """
    vlan = ForeignKey(Vlan, verbose_name=_('vlan'),
                      help_text=_('Network the interface belongs to.'))
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
        return "%s - %s - %s" % (self.template, self.vlan, self.managed)


class Interface(Model):

    """Network interface for an instance.
    """
    vlan = ForeignKey(Vlan, verbose_name=_('vlan'),
                      related_name="vm_interface")
    host = ForeignKey(Host, verbose_name=_('host'),  blank=True, null=True)
    instance = ForeignKey('Instance', verbose_name=_('instance'),
                          related_name='interface_set')

    class Meta:
        app_label = 'vm'
        db_table = 'vm_interface'

    def __unicode__(self):
        return 'cloud-' + str(self.instance.id) + '-' + str(self.vlan.vid)

    @property
    def mac(self):
        try:
            return self.host.mac
        except:
            return Interface.generate_mac(self.instance, self.vlan)

    @classmethod
    def generate_mac(cls, instance, vlan):
        """Generate MAC address for a VM instance on a VLAN.
        """
        # MAC 02:XX:XX:XX:XX:XX
        #        \________/\__/
        #           VM ID   VLAN ID
        class mac_custom(mac_unix):
            word_fmt = '%.2X'
        i = instance.id & 0xfffffff
        v = vlan.vid & 0xfff
        m = (0x02 << 40) | (i << 12) | v
        return EUI(m, dialect=mac_custom)

    def get_vmnetwork_desc(self):
        return {
            'name': self.__unicode__(),
            'bridge': 'cloud',
            'mac': str(self.mac),
            'ipv4': str(self.host.ipv4) if self.host is not None else None,
            'ipv6': str(self.host.ipv6) if self.host is not None else None,
            'vlan': self.vlan.vid,
            'managed': self.host is not None
        }

    def deploy(self, user=None, task_uuid=None):
        net_tasks.create.apply_async(
            args=[self.get_vmnetwork_desc()],
            queue=self.instance.get_remote_queue_name('net'))

    def destroy(self, user=None, task_uuid=None):
        net_tasks.destroy.apply_async(
            args=[self.get_vmnetwork_desc()],
            queue=self.instance.get_remote_queue_name('net'))
        if self.host is not None:
            self.host.delete()

    @classmethod
    def create(cls, instance, vlan, managed, owner=None):
        """Create a new interface for a VM instance to the specified VLAN.
        """
        if managed:
            host = Host()
            host.vlan = vlan
            # TODO change Host's mac field's type to EUI in firewall
            host.mac = str(cls.generate_mac(instance, vlan))
            host.hostname = instance.vm_name
            # Get adresses from firewall
            addresses = vlan.get_new_address()
            host.ipv4 = addresses['ipv4']
            host.ipv6 = addresses['ipv6']
            host.owner = owner
            if vlan.network_type == 'public':
                host.shared_ip = False
                host.pub_ipv4 = None
            elif vlan.network_type == 'portforward':
                host.shared_ip = True
                host.pub_ipv4 = vlan.snat_ip
            host.full_clean()
            host.save()
            host.enable_net()
            from .instance import ACCESS_PROTOCOLS
            port, proto = ACCESS_PROTOCOLS[instance.access_method][1:3]
            host.add_port(proto, private=port)
        else:
            host = None

        iface = cls(vlan=vlan, host=host, instance=instance)
        iface.save()
        return iface

    def save_as_template(self, instance_template):
        """Create a template based on this interface.
        """
        i = InterfaceTemplate(vlan=self.vlan, managed=self.host is not None,
                              template=instance_template)
        i.save()
        return i
