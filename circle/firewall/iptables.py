import logging
import re
from collections import OrderedDict

logger = logging.getLogger()

ipv4_re = re.compile(
    r'^(25[0-5]|2[0-4]\d|[0-1]?\d?\d)(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}')


class InvalidRuleExcepion(Exception):
    pass


class IptRule(object):

    def __init__(self, priority=1000, action=None, src=None, dst=None,
                 proto=None, sport=None, dport=None, extra=None,
                 ipv4_only=False):
        if proto not in ['tcp', 'udp', 'icmp', None]:
            raise InvalidRuleExcepion()
        if proto not in ['tcp', 'udp'] and (sport is not None or
                                            dport is not None):
            raise InvalidRuleExcepion()

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
        self.sport = sport
        self.dport = dport

        self.extra = extra
        self.ipv4_only = (ipv4_only or
                          extra is not None and bool(ipv4_re.search(extra)))

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
                            ('extra', '%s'),
                            ('action', '-g %s')])
        params = [opts[param] % getattr(self, param)
                  for param in opts
                  if getattr(self, param) is not None]
        return ' '.join(params)


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
        return sorted(list(self.rules))

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
