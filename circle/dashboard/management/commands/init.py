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

from __future__ import unicode_literals, absolute_import

import logging

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from firewall.models import Vlan, VlanGroup, Domain, Firewall, Rule
from storage.models import DataStore
from vm.models import Lease


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--force', action="store_true")
        parser.add_argument('--external-net')
        parser.add_argument('--management-net')
        parser.add_argument('--vm-net')
        parser.add_argument('--external-if')
        parser.add_argument('--management-if')
        parser.add_argument('--vm-if')
        parser.add_argument('--datastore-queue')
        parser.add_argument('--firewall-queue')
        parser.add_argument('--admin-user')
        parser.add_argument('--admin-pass')

    def create(self, model, field, **kwargs):
        value = kwargs[field]
        qs = model.objects.filter(**{field: value})[:1]
        if not qs.exists():
            obj = model.objects.create(**kwargs)
            logger.info('New %s: %s', model, obj)
            self.changed = True
            return obj
        else:
            return qs[0]

# http://docs.saltstack.com/en/latest/ref/states/all/salt.states.cmd.html
    def print_state(self):
        self.stdout.write("\nchanged=%s" % ("yes" if self.changed else "no"))

    def handle(self, *args, **options):
        self.changed = False

        if (DataStore.objects.exists() and Vlan.objects.exists() and
                not options['force']):
            self.print_state()
            return

        admin = self.create(User, 'username', username=options['admin_user'],
                            is_superuser=True, is_staff=True)
        admin.set_password(options['admin_pass'])
        admin.save()

        self.create(DataStore, 'path', path='/datastore', name='default',
                    hostname=options['datastore_queue'])

        # leases
        self.create(Lease, 'name', name='lab',
                    suspend_interval_seconds=3600 * 5,
                    delete_interval_seconds=3600 * 24 * 7)

        self.create(Lease, 'name', name='project',
                    suspend_interval_seconds=3600 * 24 * 30,
                    delete_interval_seconds=3600 * 24 * 30 * 6)

        self.create(Lease, 'name', name='server',
                    suspend_interval_seconds=3600 * 24 * 365,
                    delete_interval_seconds=3600 * 24 * 365 * 3)

        net_domain = self.create(Domain, 'name', name='net.example.com',
                                 owner=admin)
        man_domain = self.create(Domain, 'name', name='man.example.com',
                                 owner=admin)
        vm_domain = self.create(Domain, 'name', name='vm.example.com',
                                owner=admin)

        # vlans
        net = self.create(Vlan, 'vid', name=options['external_if'], vid=4,
                          network4=options['external_net'], domain=net_domain)

        man = self.create(Vlan, 'vid', name=options['management_if'], vid=3,
                          dhcp_pool='manual',
                          network4=options['management_net'],
                          domain=man_domain,
                          snat_ip=options['external_net'].split('/')[0])
        man.snat_to.add(net)
        man.snat_to.add(man)

        vm = self.create(Vlan, 'vid', name=options['vm_if'], vid=2,
                         dhcp_pool='manual',
                         network4=options['vm_net'], domain=vm_domain,
                         snat_ip=options['external_net'].split('/')[0])
        vm.snat_to.add(net)
        vm.snat_to.add(vm)

        # default vlan groups
        vg_all = self.create(VlanGroup, 'name', name='all')
        vg_all.vlans.add(vm, man, net)

        vg_pf = self.create(VlanGroup, 'name', name='portforward')
        vg_pf.vlans.add(vm, man, net)

        vg_net = self.create(VlanGroup, 'name', name='net')
        vg_net.vlans.add(net)

        # firewall rules
        fw = self.create(Firewall, 'name', name=options['firewall_queue'])

        self.create(Rule, 'description', description='default output rule',
                    direction='out', action='accept',
                    foreign_network=vg_all, firewall=fw)

        self.create(Rule, 'description', description='portal https',
                    direction='in', action='accept', proto='tcp', dport=443,
                    foreign_network=vg_all, firewall=fw)

        self.create(Rule, 'description', description='portal http',
                    direction='in', action='accept', proto='tcp', dport=80,
                    foreign_network=vg_all, firewall=fw)

        self.create(Rule, 'description', description='ssh',
                    direction='in', action='accept', proto='tcp', dport=22,
                    foreign_network=vg_all, firewall=fw)

        # vlan rules
        self.create(Rule, 'description', description='allow vm->net',
                    direction='out', action='accept',
                    foreign_network=vg_net, vlan=vm)

        self.create(Rule, 'description', description='allow man->net',
                    direction='out', action='accept',
                    foreign_network=vg_net, vlan=man)

        self.print_state()
