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

import logging
import re
from collections import OrderedDict

logger = logging.getLogger()

ipv4_re = re.compile(
    r'(25[0-5]|2[0-4]\d|[0-1]?\d?\d)(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}')

multiport_re = re.compile(r'^\d+\:\d+$')


class InvalidRuleExcepion(Exception):
    pass


class IptRule(object):

    def __init__(self, priority=1000, action=None, src=None, dst=None,
                 proto=None, sport=None, sports=None,
                 dport=None, dports=None,
                 extra=None, ipv4_only=False, comment=None):
        if proto not in ['tcp', 'udp', 'icmp', None]:
            raise InvalidRuleExcepion()
        if proto not in ['tcp', 'udp'] and (sport is not None or
                                            sports is not None or
                                            dport is not None or
                                            dports is not None):
            raise InvalidRuleExcepion()

        self.check_multiport(sports)
        self.check_multiport(dports)

        self.priority = int(priority)
        self.action = action

        (self.src4, self.src6) = (None, None)
        if isinstance(src, tuple):
            (self.src4, self.src6) = src
            if not self.src6:
                ipv4_only = True
        (self.dst4, self.dst6) = (None, None)
        if isinstance(dst, tuple):
            (self.dst4, self.dst6) = dst
            if not self.dst6:
                ipv4_only = True

        self.proto = proto
        self.sport = sport if sports is None else None
        self.dport = dport if dports is None else None
        self.sports = sports
        self.dports = dports

        if sports is not None or dports is not None:
            self.multiport = ""
        else:
            self.multiport = None

        self.extra = extra
        self.ipv4_only = (ipv4_only or
                          extra is not None and bool(ipv4_re.search(extra)))
        self.comment = comment

    def __hash__(self):
        return hash(frozenset(self.__dict__.items()))

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __lt__(self, other):
        return self.priority < other.priority

    def __repr__(self):
        return '<IptRule: @%d %s >' % (self.priority, self.compile())

    def __unicode__(self):
        return self.__repr__()

    def compile(self, proto='ipv4'):
        opts = OrderedDict([('src4' if proto == 'ipv4' else 'src6', '-s %s'),
                            ('dst4' if proto == 'ipv4' else 'dst6', '-d %s'),
                            ('proto', '-p %s'),
                            ('sport', '--sport %s'),
                            ('dport', '--dport %s'),
                            ('multiport', '-m multiport %s'),
                            ('sports', '--sports %s'),
                            ('dports', '--dports %s'),
                            ('extra', '%s'),
                            ('comment', '-m comment --comment "%s"'),
                            ('action', '-g %s')])
        params = [opts[param] % getattr(self, param)
                  for param in opts
                  if getattr(self, param) is not None]
        return ' '.join(params)

    def check_multiport(self, ports):
        if ports is not None and not multiport_re.match(ports):
            raise InvalidRuleExcepion()


class IptChain(object):
    nat_chains = ('PREROUTING', 'POSTROUTING')
    builtin_chains = ('FORWARD', 'INPUT', 'OUTPUT') + nat_chains

    def __init__(self, name):
        self.rules = set()
        self.name = name

    def add(self, *args, **kwargs):
        for rule in args:
            self.rules.add(rule)

    def sort(self):
        return sorted(list(self.rules), reverse=True)

    def __len__(self):
        return len(self.rules)

    def __repr__(self):
        return '<IptChain: %s %s>' % (self.name, self.rules)

    def __unicode__(self):
        return self.__repr__()

    def compile(self, proto='ipv4'):
        assert proto in ('ipv4', 'ipv6')
        prefix = '-A %s ' % self.name
        return '\n'.join([prefix + rule.compile(proto)
                          for rule in self.sort()
                          if not (proto == 'ipv6' and rule.ipv4_only)])

    def compile_v6(self):
        return self.compile('ipv6')
