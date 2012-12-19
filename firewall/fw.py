#!/usr/bin/env python

#from django.core.management import setup_environ
#from teszt import settings

#setup_environ(settings)

from django.contrib import auth
from firewall import models
import os

import subprocess
import re
DNS_SERVER = "152.66.243.60"


class firewall:
	IPV6=False
	SZABALYOK=[]
	SZABALYOK_NAT=[]
	vlans = None
	dmz = None
	pub = None
	hosts = None
	fw = None

	def iptables(self, s):
		self.SZABALYOK.append(s)

	def iptablesnat(self, s):
		self.SZABALYOK_NAT.append(s)

	def host2vlan(self, host, rule):
		if(self.IPV6):
			ipaddr = host.ipv6 + "/112"
		else:
			ipaddr = host.ipv4

		extra = rule.extra
		if(rule.nat and rule.direction):
			extra = re.sub(r'--dport [0-9]+', '--dport %i' %rule.nat_dport, rule.extra)

		for vlan in rule.vlan.all():
			if(rule.action):
				if((not rule.direction) and vlan.name == "PUB"):
					action = "PUB_OUT"
				else:
					action = "LOG_ACC"
			else:
				action = "LOG_DROP"

			if(rule.direction): #HOSTHOZ megy
				self.iptables("-A %s_%s -d %s %s -g %s" % (vlan, host.vlan, ipaddr, extra, action));
			else:
				self.iptables("-A %s_%s -s %s %s -g %s" % (host.vlan, vlan, ipaddr, extra, action));


	def fw2vlan(self, rule):	
		for vlan in rule.vlan.all():
			if(rule.direction): #HOSTHOZ megy
				self.iptables("-A INPUT -i %s %s -g %s" % (vlan.interface, rule.extra, "LOG_ACC" if rule.action else "LOG_DROP"));
			else:
				self.iptables("-A OUTPUT -o %s %s -g %s" % (vlan.interface, rule.extra, "LOG_ACC" if rule.action else "LOG_DROP"));

	def vlan2vlan(self, l_vlan, rule):
		for vlan in rule.vlan.all():
			if(rule.action):
				if((not rule.direction) and vlan.name == "PUB"):
					action = "PUB_OUT"
				else:
					action = "LOG_ACC"
			else:
				action = "LOG_DROP"

			if(rule.direction): #HOSTHOZ megy
				self.iptables("-A %s_%s %s -g %s" % (vlan, l_vlan, rule.extra, action));
			else:
				self.iptables("-A %s_%s %s -g %s" % (l_vlan, vlan, rule.extra, action));			


	def prerun(self):
		self.iptables("*filter")
		self.iptables(":INPUT DROP [88:6448]")
		self.iptables(":FORWARD DROP [0:0]")
		self.iptables(":OUTPUT DROP [50:6936]")

		#inicialize logging
		self.iptables("-N LOG_DROP")
		#windows port scan are silently dropped
		self.iptables("-A LOG_DROP -p tcp --dport 445 -j DROP")
		self.iptables("-A LOG_DROP -p udp --dport 137 -j DROP")
		self.iptables("-A LOG_DROP -j LOG --log-level 7 --log-prefix \"[ipt][drop]\"")
		self.iptables("-A LOG_DROP -j DROP")
		self.iptables("-N LOG_ACC")
		self.iptables("-A LOG_ACC -j LOG --log-level 7 --log-prefix \"[ipt][isok]\"")
		self.iptables("-A LOG_ACC -j ACCEPT")

		if not self.IPV6:
			#The chain which test is a packet has a valid public destination IP
			#(RFC-3330) packages passing this chain has valid destination IP addressed
			self.iptables("-N r_pub_dIP")
			self.iptables("-A r_pub_dIP -d 0.0.0.0/8 -g LOG_DROP")
			self.iptables("-A r_pub_dIP -d 169.254.0.0/16 -g LOG_DROP")
			self.iptables("-A r_pub_dIP -d 172.16.0.0/12 -g LOG_DROP")
			self.iptables("-A r_pub_dIP -d 192.0.2.0/24 -g LOG_DROP")
			self.iptables("-A r_pub_dIP -d 192.168.0.0/16 -g LOG_DROP")
			self.iptables("-A r_pub_dIP -d 127.0.0.0/8 -g LOG_DROP")
			#self.iptables("-A r_pub_dIP -d 10.0.0.0/8 -g LOG_DROP")

			#The chain which test is a packet has a valid public source IP
			#(RFC-3330) packages passing this chain has valid destination IP addressed
			self.iptables("-N r_pub_sIP")
			self.iptables("-A r_pub_sIP -s 0.0.0.0/8 -g LOG_DROP")
			self.iptables("-A r_pub_sIP -s 169.254.0.0/16 -g LOG_DROP")
			self.iptables("-A r_pub_sIP -s 172.16.0.0/12 -g LOG_DROP")
			self.iptables("-A r_pub_sIP -s 192.0.2.0/24 -g LOG_DROP")
			self.iptables("-A r_pub_sIP -s 192.168.0.0/16 -g LOG_DROP")
			self.iptables("-A r_pub_sIP -s 127.0.0.0/8 -g LOG_DROP")
			#self.iptables("-A r_pub_sIP -s 10.0.0.0/8 -g LOG_DROP")

			#chain which tests if the destination specified by the DMZ host is valid
			self.iptables("-N r_DMZ_dIP")
			self.iptables("-A r_DMZ_dIP -d 10.2.0.0/16 -j RETURN")
			self.iptables("-A r_DMZ_dIP -j r_pub_dIP")

		self.iptables("-N PUB_OUT")
		if not self.IPV6:
			self.iptables("-A PUB_OUT -j r_pub_dIP")
	#	self.iptables("-A PUB_OUT -s $HOST_pbx2_DMZ_IP -p tcp --dport 25 -j LOG_ACC")
		self.iptables("-A PUB_OUT -p tcp --dport 25 -j LOG_DROP")
		self.iptables("-A PUB_OUT -p tcp --dport 445 -j LOG_DROP")
		self.iptables("-A PUB_OUT -p udp --dport 445 -j LOG_DROP")

		self.iptables("-A FORWARD -m state --state INVALID -g LOG_DROP")
		self.iptables("-A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT")
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


		#portforward
		for host in self.hosts.filter(pub_ipv4=None):
			for rule in host.rules.filter(nat=True, direction=True):
				self.iptablesnat("-A PREROUTING -d %s %s -j DNAT --to-destination %s:%s" % (host.vlan.snat_ip, rule.extra, host.ipv4, rule.nat_dport))

		#sajat publikus ipvel rendelkezo gepek szabalyai
		for host in self.hosts:
			if(host.pub_ipv4):
				self.iptablesnat("-A PREROUTING -d %s -j DNAT --to-destination %s" % (host.pub_ipv4, host.ipv4))
				self.iptablesnat("-A POSTROUTING -s %s -j SNAT --to-source %s" % (host.ipv4, host.pub_ipv4))

		#alapertelmezett nat szabalyok a vlanokra
		for s_vlan in self.vlans:
			if(s_vlan.snat_ip):
				for d_vlan in s_vlan.snat_to.all():
					self.iptablesnat("-A POSTROUTING -s %s -o %s -j SNAT --to-source %s" % (s_vlan.net_ipv4(), d_vlan.interface, s_vlan.snat_ip))


		#bedrotozott szabalyok
		self.iptablesnat("-A POSTROUTING -s 10.5.0.0/16 -o vlan0003 -j SNAT --to-source 10.3.255.254") #man elerheto legyen
		self.iptablesnat("-A POSTROUTING -s 10.5.0.0/16 -o vlan0008 -j SNAT --to-source 10.0.0.247") #wolf halozat a nyomtatashoz
		self.iptablesnat("-A POSTROUTING -s 10.3.0.0/16 -o vlan0006 -j SNAT --to-source %s" % self.pub.ipv4) #kulonben nemmegy a du

		self.iptablesnat("COMMIT")

	def ipt_filter(self):
		regexp = re.compile('[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
		regexp_icmp = re.compile('icmp');

		#futas elotti dolgok
		self.prerun()

		#tuzfal sajat szabalyai
		for f in self.fw:
			for rule in f.rules.all():
				self.fw2vlan(rule)

		#zonak kozotti lancokra ugras
		for s_vlan in self.vlans:
			for d_vlan in self.vlans:
				self.iptables("-N %s_%s" % (s_vlan, d_vlan))
				self.iptables("-A FORWARD -i %s -o %s -g %s_%s" % (s_vlan.interface, d_vlan.interface, s_vlan, d_vlan))

		#hosztok szabalyai
		for i_vlan in self.vlans:
			for i_host in i_vlan.host_set.all():
				for group in i_host.groups.all():
					for rule in group.rules.all():
						self.host2vlan(i_host, rule)
				for rule in i_host.rules.all():
					self.host2vlan(i_host, rule)

		#vlanok kozotti kommunikacio engedelyezese
		for s_vlan in self.vlans:
			for rule in s_vlan.rules.all():
				self.vlan2vlan(s_vlan, rule)

		#zonak kozotti lancokat zarja le
		for s_vlan in self.vlans:
			for d_vlan in self.vlans:
				self.iptables("-A %s_%s -g LOG_DROP" % (s_vlan, d_vlan))

		#futas utani dolgok
		self.postrun()

		if self.IPV6:
			self.SZABALYOK = [x for x in self.SZABALYOK if not regexp.search(x)]
			self.SZABALYOK = [regexp_icmp.sub('icmpv6', x) for x in self.SZABALYOK]
	#####

	def __init__(self, IPV6=False):
		self.SZABALYOK=[]
		self.SZABALYOK=[]
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



def dns():
	vlans = models.Vlan.objects.all()
	regex = re.compile(r'^([0-9]+)\.([0-9]+)\.([0-9]+)\.([0-9]+)$')
	DNS = []
	DNS.append("=cloud.ik.bme.hu:152.66.243.98:600::\n")
#tarokkknak
	DNS.append("^%s.dns1.%s.%s.%s.in-addr.arpa:%s:600::\n" % (75, 243, 66, 152, "se.hpc.iit.bme.hu"))
	DNS.append("^%s.dns1.%s.%s.%s.in-addr.arpa:%s:600::\n" % (76, 243, 66, 152, "ce.hpc.iit.bme.hu"))
	DNS.append("^%s.dns1.%s.%s.%s.in-addr.arpa:%s:600::\n" % (77, 243, 66, 152, "mon.hpc.iit.bme.hu"))

	for i_vlan in vlans:
		m = regex.search(i_vlan.net4)
		if(i_vlan.name != "DMZ" and i_vlan.name != "PUB"):
			DNS.append("Z%s.%s.in-addr.arpa:dns1.ik.bme.hu:ez.miez::::::600\n" % (m.group(2), m.group(1)))
			DNS.append("&%s.%s.in-addr.arpa::dns1.ik.bme.hu:600::\n" % (m.group(2), m.group(1)))
			DNS.append("Z%s:dns1.ik.bme.hu:ez.miez::::::600\n" % i_vlan.domain)
			DNS.append("&%s::dns1.ik.bme.hu:600::\n" % i_vlan.domain)
			if(i_vlan.name == "WAR"):
				DNS.append("Zdns1.%s.%s.%s.in-addr.arpa:dns1.ik.bme.hu:ez.miez::::::600\n" % (m.group(3), m.group(2), m.group(1)))
				DNS.append("&dns1.%s.%s.%s.in-addr.arpa::dns1.ik.bme.hu:600::\n" % (m.group(3), m.group(2), m.group(1)))
		for i_host in i_vlan.host_set.all():
			ipv4 = ( i_host.pub_ipv4 if i_host.pub_ipv4 else i_host.ipv4 )
			m2 = regex.search(ipv4)
			DNS.append("=%s.%s:%s:600::\n" % (i_host.hostname, i_vlan.domain, ipv4))
			DNS.append("^%s.dns1.%s.%s.%s.in-addr.arpa:%s.%s:600::\n" % (m2.group(4), m2.group(3), m2.group(2), m2.group(1), i_host.hostname, i_vlan.domain))

	process = subprocess.Popen(['/usr/bin/ssh', 'tinydns@%s' % DNS_SERVER], shell=False, stdin=subprocess.PIPE)
	process.communicate("\n".join(DNS)+"\n")



def dhcp():
	vlans = models.Vlan.objects.all()
	regex = re.compile(r'^([0-9]+)\.([0-9]+)\.[0-9]+\.[0-9]+\s+([0-9]+)\.([0-9]+)\.[0-9]+\.[0-9]+$')
	DHCP = []

#/tools/dhcp3/dhcpd.conf.generated

	for i_vlan in vlans:
		if(i_vlan.dhcp_pool):
			m = regex.search(i_vlan.dhcp_pool)
			if(m or i_vlan.dhcp_pool == "manual"):
				DHCP.append ('''
				#%(name)s - %(interface)s
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
					'netmask': "255.255.0.0", #TODO: ez ne legyen belehardkodolva
					'domain': i_vlan.domain,
					'router': i_vlan.ipv4,
					'ntp': i_vlan.ipv4,
					'dnsserver': DNS_SERVER,
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
#	print "\n".join(DHCP)+"\n"
	process.communicate("\n".join(DHCP)+"\n")

#ipt_filter()
#ipt_nat()
#process = subprocess.Popen(['/usr/bin/sudo', 'iptables-restore'], shell=False, stdin=subprocess.PIPE)
#process.communicate("\n".join(SZABALYOK)+"\n"+"\n".join(SZABALYOK_NAT)+"\n")

#blabla = firewall()


#process = subprocess.Popen(['/usr/bin/sudo', 'ip6tables-restore'], shell=False, stdin=subprocess.PIPE)
#process.communicate("\n".join(SZABALYOK)+"\n")

#dns()
#dhcp()



i=2
'''
for mac, name, ipend in [("18:a9:05:64:19:aa", "mega6", 16), ("00:1e:0b:e9:79:1e", "blade1", 21), ("00:22:64:9c:fd:34", "blade2", 22), ("00:1e:0b:ec:65:46", "blade3", 23), ("b4:b5:2f:61:d2:5a", "cloud-man", 1)]:
	h1 = models.Host(hostname= name, vlan=models.Vlan.objects.get(vid=3), mac=mac, ipv4="10.3.1.%d" % ipend, ipv6="2001:738:2001:4031:3:1:%d:0" % ipend, owner=auth.models.User.objects.get(username="bd"))
	try:
		h1.save()
		h1.groups.add(models.Group.objects.get(name="netezhet manbol"))
		h1.save()
#		i = i + 1
	except:
		print "nemok %s" % name
'''
	
#try:
#	h1.save()
#	h1.groups.add(models.Group.objects.get(name="irodai gep"))
#	h1.save()
#except:
#	print "nemsikerult"



















