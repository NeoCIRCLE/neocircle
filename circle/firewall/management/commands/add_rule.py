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

from django.core.management.base import BaseCommand, CommandError

from firewall.models import Vlan, VlanGroup, Rule
from django.contrib.auth.models import User


class Command(BaseCommand):

    def add_arguments(self, parser):

        group = parser.add_mutually_exclusive_group(required=True)

        group.add_argument('--port',
                           action='store',
                           dest='port',
                           type=int,
                           help='port which will open (0-65535)')

        group.add_argument('--port-range',
                           action='store',
                           dest='range',
                           type=int,
                           nargs=2,
                           help='closed port range which will open (0-65535)',
                           metavar=('LOWER', 'HIGHER'))

        parser.add_argument('--protocol',
                            action='store',
                            dest='proto',
                            required=True,
                            choices=('tcp', 'udp', 'icmp'),
                            help='protocol name')

        parser.add_argument('--action',
                            action='store',
                            dest='action',
                            default='accept',
                            choices=('accept', 'drop', 'ignore'),
                            help='action of the rule')

        parser.add_argument('--dir',
                            action='store',
                            dest='dir',
                            default='in',
                            choices=('in', 'out'),
                            help='direction of the rule')

        parser.add_argument('--vlan',
                            action='store',
                            dest='vlan',
                            required=True,
                            help='vlan name where the port will open')

        parser.add_argument('--vlan-group',
                            action='store',
                            dest='vlan_group',
                            required=True,
                            help='vlan group name where the port will open')

        parser.add_argument('--owner',
                            action='store',
                            dest='owner',
                            required=True,
                            help='name of user who owns the rule')

    def handle(self, *args, **options):

        port = options['port']
        range = options['range']
        proto = options['proto']
        action = options['action']
        dir = options['dir']
        owner = options['owner']
        vlan = options['vlan']
        fnet = options['vlan_group']

        try:
            owner = User.objects.get(username=owner)
            vlan = Vlan.objects.get(name=vlan)
            fnet = VlanGroup.objects.get(name=fnet)
        except User.DoesNotExist:
            raise CommandError("User '%s' does not exist" % owner)
        except Vlan.DoesNotExist:
            raise CommandError("Vlan '%s' does not exist" % vlan)
        except VlanGroup.DoesNotExist:
            raise CommandError("VlanGroup '%s' does not exist" % fnet)

        if port:
            self.validate_port(port)
            rule = self.make_rule(port, proto, action, dir, owner, vlan, fnet)
            rule.save()
        else:
            lower = min(range)
            higher = max(range)
            self.validate_port(lower)
            self.validate_port(higher)

            rules = []

            for port in xrange(lower, higher+1):
                rule = self.make_rule(port, proto, action, dir,
                                      owner, vlan, fnet)
                rules.append(rule)

            Rule.objects.bulk_create(rules)

    def make_rule(self, port, proto, action, dir, owner, vlan, fnet):

        rule = Rule(direction=dir, dport=port, proto=proto, action=action,
                    vlan=vlan, foreign_network=fnet, owner=owner)

        if self.is_exist(port, proto, action, dir, owner, vlan, fnet):
            raise CommandError('Rule does exist, yet: %s' % unicode(rule))

        rule.full_clean()

        return rule

    def is_exist(self, port, proto, action, dir, owner, vlan, fnet):

        rules = Rule.objects.filter(direction=dir,
                                    dport=port,
                                    proto=proto,
                                    action=action,
                                    vlan=vlan,
                                    foreign_network=fnet,
                                    owner=owner)
        return rules.exists()

    def validate_port(self, port):
        if port < 0 or port > 65535:
            raise CommandError("Port '%i' not in range [0-65535]" % port)
