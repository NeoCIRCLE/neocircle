from django.contrib import auth
from firewall import models
from modeldict import *
import os
from cloud.settings import firewall_settings as settings

import subprocess
import re
import json


class firewall:
    IPV6=False
    SZABALYOK = None
    SZABALYOK_NAT = []
    vlans = None
    dmz = None
    pub = None
    hosts = None
    fw = None

    def dportsport(self, rule, repl=True):
        retval = " "
        if(rule.proto == "tcp" or rule.proto == "udp"):
            retval = "-p %s " % rule.proto
            if(rule.sport):
                retval += " --sport %s " % rule.sport
            if(rule.dport):
                retval += " --dport %s " % ( rule.nat_dport if (repl and rule.nat and rule.direction == '1') else rule.dport )
        elif(rule.proto == "icmp"):
            retval = "-p %s " % rule.proto
        return retval


    def iptables(self, s):
        self.SZABALYOK.append(s)

    def iptablesnat(self, s):
        self.SZABALYOK_NAT.append(s)

    def host2vlan(self, host, rule):
        if rule.foreign_network is None:
            return

        if(self.IPV6 and host.ipv6):
            ipaddr = host.ipv6 + "/112"
        else:
            ipaddr = host.ipv4

        dport_sport = self.dportsport(rule)

        for vlan in rule.foreign_network.vlans.all():
            if(rule.accept):
                if(rule.direction == '0' and vlan.name == "PUB"):
                    if(rule.dport == 25):
                        self.iptables("-A PUB_OUT -s %s %s -p tcp --dport 25 -j LOG_ACC" % (ipaddr, rule.extra))
                        break
                    action = "PUB_OUT"
                else:
                    action = "LOG_ACC"
            else:
                action = "LOG_DROP"

            if(rule.direction == '1'): # HOSTHOZ megy
                self.iptables("-A %s_%s -d %s %s %s -g %s" % (vlan, host.vlan, ipaddr, dport_sport, rule.extra, action))
            else:
                self.iptables("-A %s_%s -s %s %s %s -g %s" % (host.vlan, vlan, ipaddr, dport_sport, rule.extra, action))


    def fw2vlan(self, rule):
        if rule.foreign_network is None:
            return

        dport_sport = self.dportsport(rule)

        for vlan in rule.foreign_network.vlans.all():
            if(rule.direction == '1'): # HOSTHOZ megy
                self.iptables("-A INPUT -i %s %s %s -g %s" % (vlan.interface, dport_sport, rule.extra, "LOG_ACC" if rule.accept else "LOG_DROP"))
            else:
                self.iptables("-A OUTPUT -o %s %s %s -g %s" % (vlan.interface, dport_sport, rule.extra, "LOG_ACC" if rule.accept else "LOG_DROP"))

    def vlan2vlan(self, l_vlan, rule):
        if rule.foreign_network is None:
            return

        dport_sport = self.dportsport(rule)

        for vlan in rule.foreign_network.vlans.all():
            if(rule.accept):
                if((rule.direction == '0') and vlan.name == "PUB"):
                    action = "PUB_OUT"
                else:
                    action = "LOG_ACC"
            else:
                action = "LOG_DROP"

            if(rule.direction == '1'): # HOSTHOZ megy
                self.iptables("-A %s_%s %s %s -g %s" % (vlan, l_vlan, dport_sport, rule.extra, action))
            else:
                self.iptables("-A %s_%s %s %s -g %s" % (l_vlan, vlan, dport_sport, rule.extra, action))


    def prerun(self):
        self.iptables("*filter")
        self.iptables(":INPUT DROP [88:6448]")
        self.iptables(":FORWARD DROP [0:0]")
        self.iptables(":OUTPUT DROP [50:6936]")

        # inicialize logging
        self.iptables("-N LOG_DROP")
        # windows port scan are silently dropped
        self.iptables("-A LOG_DROP -p tcp --dport 445 -j DROP")
        self.iptables("-A LOG_DROP -p udp --dport 137 -j DROP")
        self.iptables("-A LOG_DROP -j LOG --log-level 7 --log-prefix \"[ipt][drop]\"")
        self.iptables("-A LOG_DROP -j DROP")
        self.iptables("-N LOG_ACC")
        self.iptables("-A LOG_ACC -j LOG --log-level 7 --log-prefix \"[ipt][isok]\"")
        self.iptables("-A LOG_ACC -j ACCEPT")

        if not self.IPV6:
            # The chain which test is a packet has a valid public destination IP
            # (RFC-3330) packages passing this chain has valid destination IP addressed
            self.iptables("-N r_pub_dIP")
            self.iptables("-A r_pub_dIP -d 0.0.0.0/8 -g LOG_DROP")
            self.iptables("-A r_pub_dIP -d 169.254.0.0/16 -g LOG_DROP")
            self.iptables("-A r_pub_dIP -d 172.16.0.0/12 -g LOG_DROP")
            self.iptables("-A r_pub_dIP -d 192.0.2.0/24 -g LOG_DROP")
            self.iptables("-A r_pub_dIP -d 192.168.0.0/16 -g LOG_DROP")
            self.iptables("-A r_pub_dIP -d 127.0.0.0/8 -g LOG_DROP")
#           self.iptables("-A r_pub_dIP -d 10.0.0.0/8 -g LOG_DROP")

            # The chain which test is a packet has a valid public source IP
            # (RFC-3330) packages passing this chain has valid destination IP addressed
            self.iptables("-N r_pub_sIP")
            self.iptables("-A r_pub_sIP -s 0.0.0.0/8 -g LOG_DROP")
            self.iptables("-A r_pub_sIP -s 169.254.0.0/16 -g LOG_DROP")
            self.iptables("-A r_pub_sIP -s 172.16.0.0/12 -g LOG_DROP")
            self.iptables("-A r_pub_sIP -s 192.0.2.0/24 -g LOG_DROP")
            self.iptables("-A r_pub_sIP -s 192.168.0.0/16 -g LOG_DROP")
            self.iptables("-A r_pub_sIP -s 127.0.0.0/8 -g LOG_DROP")
            # self.iptables("-A r_pub_sIP -s 10.0.0.0/8 -g LOG_DROP")

            # chain which tests if the destination specified by the DMZ host is valid
            self.iptables("-N r_DMZ_dIP")
            self.iptables("-A r_DMZ_dIP -d 10.2.0.0/16 -j RETURN")
            self.iptables("-A r_DMZ_dIP -j r_pub_dIP")

        self.iptables("-N PUB_OUT")
        if not self.IPV6:
            self.iptables("-A PUB_OUT -j r_pub_dIP")

        self.iptables("-A FORWARD -m state --state INVALID -g LOG_DROP")
        self.iptables("-A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT")
        self.iptables("-A FORWARD -p icmp --icmp-type echo-request -g LOG_ACC")
        if not self.IPV6:
            self.iptables("-A FORWARD -j r_pub_sIP -o pub")
        self.iptables("-A INPUT -m state --state INVALID -g LOG_DROP")
        self.iptables("-A INPUT -i lo -j ACCEPT")
        if not self.IPV6:
            self.iptables("-A INPUT -j r_pub_sIP")
        self.iptables("-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT")

        self.iptables("-A OUTPUT -m state --state INVALID -g LOG_DROP")
        self.iptables("-A OUTPUT -o lo -j ACCEPT")
        self.iptables("-A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT")


    def postrun(self):
        self.iptables("-A PUB_OUT -s 152.66.243.160/27 -p tcp --dport 25 -j LOG_ACC")
        self.iptables("-A PUB_OUT -s 152.66.243.160/27 -p tcp --dport 445 -j LOG_ACC")
        self.iptables("-A PUB_OUT -p tcp --dport 25 -j LOG_DROP")
        self.iptables("-A PUB_OUT -p tcp --dport 445 -j LOG_DROP")
        self.iptables("-A PUB_OUT -p udp --dport 445 -j LOG_DROP")

        self.iptables("-A PUB_OUT -g LOG_ACC")
        self.iptables("-A FORWARD -g LOG_DROP")
        self.iptables("-A INPUT -g LOG_DROP")
        self.iptables("-A OUTPUT -g LOG_DROP")
        self.iptables("COMMIT")




    def ipt_nat(self):
        self.iptablesnat("*nat")
        self.iptablesnat(":PREROUTING ACCEPT [0:0]")
        self.iptablesnat(":INPUT ACCEPT [0:0]")
        self.iptablesnat(":OUTPUT ACCEPT [1:708]")
        self.iptablesnat(":POSTROUTING ACCEPT [1:708]")


        # portforward
        for host in self.hosts.exclude(pub_ipv4=None):
            for rule in host.rules.filter(nat=True, direction='1'):
                dport_sport = self.dportsport(rule, False)
                if host.vlan.snat_ip:
                    self.iptablesnat("-A PREROUTING -d %s %s %s -j DNAT --to-destination %s:%s" % (host.pub_ipv4, dport_sport, rule.extra, host.ipv4, rule.nat_dport))

        # sajat publikus ipvel rendelkezo gepek szabalyai
        for host in self.hosts.exclude(shared_ip=True):
            if(host.pub_ipv4):
                self.iptablesnat("-A PREROUTING -d %s -j DNAT --to-destination %s" % (host.pub_ipv4, host.ipv4))
                self.iptablesnat("-A POSTROUTING -s %s -j SNAT --to-source %s" % (host.ipv4, host.pub_ipv4))

        # alapertelmezett nat szabalyok a vlanokra
        for s_vlan in self.vlans:
            if(s_vlan.snat_ip):
                for d_vlan in s_vlan.snat_to.all():
                    self.iptablesnat("-A POSTROUTING -s %s -o %s -j SNAT --to-source %s" % (s_vlan.net_ipv4(), d_vlan.interface, s_vlan.snat_ip))


        # bedrotozott szabalyok
        self.iptablesnat("-A POSTROUTING -s 10.5.0.0/16 -o vlan0003 -j SNAT --to-source 10.3.255.254") # man elerheto legyen
        self.iptablesnat("-A POSTROUTING -s 10.5.0.0/16 -o vlan0008 -j SNAT --to-source 10.0.0.247") # wolf halozat a nyomtatashoz
        self.iptablesnat("-A POSTROUTING -s 10.3.0.0/16 -o vlan0002 -j SNAT --to-source %s" % self.pub.ipv4) # kulonben nemmegy a du

        self.iptablesnat("COMMIT")

    def ipt_filter(self):
        regexp = re.compile('[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
        regexp_icmp = re.compile('icmp')

        # futas elotti dolgok
        self.prerun()

        # tuzfal sajat szabalyai
        for f in self.fw:
            for rule in f.rules.all():
                self.fw2vlan(rule)

        # zonak kozotti lancokra ugras
        for s_vlan in self.vlans:
            for d_vlan in self.vlans:
                self.iptables("-N %s_%s" % (s_vlan, d_vlan))
                self.iptables("-A FORWARD -i %s -o %s -g %s_%s" % (s_vlan.interface, d_vlan.interface, s_vlan, d_vlan))

        # hosztok szabalyai
        for i_vlan in self.vlans:
            for i_host in i_vlan.host_set.all():
                for group in i_host.groups.all():
                    for rule in group.rules.all():
                        self.host2vlan(i_host, rule)
                for rule in i_host.rules.all():
                    self.host2vlan(i_host, rule)

        # vlanok kozotti kommunikacio engedelyezese
        for s_vlan in self.vlans:
            for rule in s_vlan.rules.all():
                self.vlan2vlan(s_vlan, rule)

        # zonak kozotti lancokat zarja le
        for s_vlan in self.vlans:
            for d_vlan in self.vlans:
                self.iptables("-A %s_%s -g LOG_DROP" % (s_vlan, d_vlan))

        # futas utani dolgok
        self.postrun()

        if self.IPV6:
            self.SZABALYOK = [x for x in self.SZABALYOK if not regexp.search(x)]
            self.SZABALYOK = [regexp_icmp.sub('icmpv6', x) for x in self.SZABALYOK]

    def __init__(self, IPV6=False):
        self.SZABALYOK=[]
        self.SZABALYOK_NAT=[]
        self.IPV6 = IPV6
        self.vlans = models.Vlan.objects.all()
        self.hosts = models.Host.objects.all()
        self.dmz = models.Vlan.objects.get(name="DMZ")
        self.pub = models.Vlan.objects.get(name="PUB")
        self.fw = models.Firewall.objects.all()
        self.ipt_filter()
        if not self.IPV6:
            self.ipt_nat()

    def reload(self):
        if self.IPV6:
            process = subprocess.Popen(['/usr/bin/ssh', 'fw2', '/usr/bin/sudo', '/sbin/ip6tables-restore', '-c'], shell=False, stdin=subprocess.PIPE)
            process.communicate("\n".join(self.SZABALYOK)+"\n")
        else:
            process = subprocess.Popen(['/usr/bin/ssh', 'fw2', '/usr/bin/sudo', '/sbin/iptables-restore', '-c'], shell=False, stdin=subprocess.PIPE)
            process.communicate("\n".join(self.SZABALYOK)+"\n"+"\n".join(self.SZABALYOK_NAT)+"\n")

    def show(self):
        if self.IPV6:
            return "\n".join(self.SZABALYOK)+"\n"
        else:
            return "\n".join(self.SZABALYOK)+"\n"+"\n".join(self.SZABALYOK_NAT)+"\n"


def ipv6_to_octal(ipv6):
    while len(ipv6.split(':')) < 8:
        ipv6 = ipv6.replace('::', ':::')
    octets = []
    for part in ipv6.split(':'):
        if not part:
            octets.extend([0, 0])
        else:
            # Pad hex part to 4 digits.
            part = '%04x' % int(part, 16)
            octets.append(int(part[:2], 16))
            octets.append(int(part[2:], 16))
    return '\\' + '\\'.join(['%03o' % x for x in octets])

def ipv4_to_arpa(ipv4, cname=False):
    m2 = re.search(r'^([0-9]+)\.([0-9]+)\.([0-9]+)\.([0-9]+)$', ipv4)
    if(cname):
        return "%s.dns1.%s.%s.%s.in-addr.arpa" % (m2.group(4), m2.group(3), m2.group(2), m2.group(1))
    else:
        return "%s.%s.%s.%s.in-addr.arpa" % (m2.group(4), m2.group(3), m2.group(2), m2.group(1))

def ipv6_to_arpa(ipv6):
    while len(ipv6.split(':')) < 8:
        ipv6 = ipv6.replace('::', ':::')
    octets = []
    for part in ipv6.split(':'):
        if not part:
            octets.extend([0, 0, 0, 0])
        else:
            # Pad hex part to 4 digits.
            part = '%04x' % int(part, 16)
            octets.insert(0, int(part[0], 16))
            octets.insert(0, int(part[1], 16))
            octets.insert(0, int(part[2], 16))
            octets.insert(0, int(part[3], 16))
    return '.'.join(['%1x' % x for x in octets]) + '.ip6.arpa'



# =fqdn:ip:ttl          A, PTR
# &fqdn:ip:x:ttl        NS
# ZfqdnSOA
# +fqdn:ip:ttl          A
# ^                     PTR
# C                     CNAME
# :                     generic

def dns():
    vlans = models.Vlan.objects.all()
    regex = re.compile(r'^([0-9]+)\.([0-9]+)\.([0-9]+)\.([0-9]+)$')
    DNS = []

    for i_vlan in vlans:
        m = regex.search(i_vlan.net4)
        rev = i_vlan.reverse_domain

        for i_host in i_vlan.host_set.all():
            ipv4 = ( i_host.pub_ipv4 if i_host.pub_ipv4 and not i_host.shared_ip else i_host.ipv4 )
            i = ipv4.split('.', 4)
            reverse = i_host.reverse if(i_host.reverse and len(i_host.reverse)) else i_host.get_fqdn()

            # ipv4
            if i_host.ipv4:
                DNS.append("^%s:%s:%s" % ((rev % { 'a': int(i[0]), 'b': int(i[1]), 'c': int(i[2]), 'd': int(i[3]) }), reverse, models.settings['dns_ttl']))

            # ipv6
            if i_host.ipv6:
                DNS.append("^%s:%s:%s" % (ipv6_to_arpa(i_host.ipv6), reverse, models.settings['dns_ttl']))

    for domain in models.Domain.objects.all():
        DNS.append("Z%s:%s:support.ik.bme.hu::::::%s" % (domain.name, settings['dns_hostname'], models.settings['dns_ttl']))

    for r in models.Record.objects.all():
        d = r.get_data()
        if d['type'] == 'A':
            DNS.append("+%s:%s:%s" % (d['name'], d['address'], d['ttl']))
        elif d['type'] == 'AAAA':
            DNS.append(":%s:28:%s:%s" % (d['name'], ipv6_to_octal(d['address']), d['ttl']))
        elif d['type'] == 'NS':
            DNS.append("&%s::%s:%s" % (d['name'], d['address'], d['ttl']))
        elif d['type'] == 'CNAME':
            DNS.append("C%s:%s:%s" % (d['name'], d['address'], d['ttl']))
        elif d['type'] == 'MX':
            mx = d['address'].split(':', 2)
            DNS.append("@%(fqdn)s::%(mx)s:%(dist)s:%(ttl)s" % {'fqdn': d['name'], 'mx': mx[1], 'dist': mx[0], 'ttl': d['ttl']})

    process = subprocess.Popen(['/usr/bin/ssh', 'tinydns@%s' % settings['dns_hostname']], shell=False, stdin=subprocess.PIPE)
    process.communicate("\n".join(DNS)+"\n")
    # print "\n".join(DNS)+"\n"


def prefix_to_mask(prefix):
    t = [0, 0, 0, 0]
    for i in range(0, 4):
        if prefix > i*8+7:
            t[i] = 255
        elif i*8 < prefix and prefix <= (i+1)*8:
            t[i] = 256 - (2 ** ((i+1)*8 - prefix))
    return ".".join([str(i) for i in t])

def dhcp():
    vlans = models.Vlan.objects.all()
    regex = re.compile(r'^([0-9]+)\.([0-9]+)\.[0-9]+\.[0-9]+\s+([0-9]+)\.([0-9]+)\.[0-9]+\.[0-9]+$')
    DHCP = []

# /tools/dhcp3/dhcpd.conf.generated

    for i_vlan in vlans:
        if(i_vlan.dhcp_pool):
            m = regex.search(i_vlan.dhcp_pool)
            if(m or i_vlan.dhcp_pool == "manual"):
                DHCP.append ('''
                # %(name)s - %(interface)s
                subnet %(net)s netmask %(netmask)s {
                  %(extra)s;
                  option domain-name "%(domain)s";
                  option routers %(router)s;
                  option domain-name-servers %(dnsserver)s;
                  option ntp-servers %(ntp)s;
                  next-server %(tftp)s;
                  authoritative;
                  filename \"pxelinux.0\";
                  allow bootp; allow booting;
                }''' % {
                    'net': i_vlan.net4,
                    'netmask': prefix_to_mask(i_vlan.prefix4),
                    'domain': i_vlan.domain,
                    'router': i_vlan.ipv4,
                    'ntp': i_vlan.ipv4,
                    'dnsserver': settings['rdns_ip'],
                    'extra': "range %s" % i_vlan.dhcp_pool if m else "deny unknown-clients",
                    'interface': i_vlan.interface,
                    'name': i_vlan.name,
                    'tftp': i_vlan.ipv4
                })

                for i_host in i_vlan.host_set.all():
                    DHCP.append ('''
                    host %(hostname)s {
                      hardware ethernet %(mac)s;
                      fixed-address %(ipv4)s;
                    }''' % {
                        'hostname': i_host.hostname,
                        'mac': i_host.mac,
                        'ipv4': i_host.ipv4,
                    })

    process = subprocess.Popen(['/usr/bin/ssh', 'fw2', 'cat > /tools/dhcp3/dhcpd.conf.generated;sudo /etc/init.d/isc-dhcp-server restart'], shell=False, stdin=subprocess.PIPE)
#   print "\n".join(DHCP)+"\n"
    process.communicate("\n".join(DHCP)+"\n")


'''
i=2
for mac, name, ipend in [("18:a9:05:64:19:aa", "mega6", 16), ("00:1e:0b:e9:79:1e", "blade1", 21), ("00:22:64:9c:fd:34", "blade2", 22), ("00:1e:0b:ec:65:46", "blade3", 23), ("b4:b5:2f:61:d2:5a", "cloud-man", 1)]:
    h1 = models.Host(hostname= name, vlan=models.Vlan.objects.get(vid=3), mac=mac, ipv4="10.3.1.%d" % ipend, ipv6="2001:738:2001:4031:3:1:%d:0" % ipend, owner=auth.models.User.objects.get(username="bd"))
    try:
        h1.save()
        h1.groups.add(models.Group.objects.get(name="netezhet manbol"))
        h1.save()
#       i = i + 1
    except:
        print "nemok %s" % name
'''

