# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import firewall.fields
from django.conf import settings
import common.models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BlacklistItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ipv4', models.GenericIPAddressField(unique=True, protocol=b'ipv4')),
                ('reason', models.TextField(verbose_name='reason', blank=True)),
                ('snort_message', models.TextField(verbose_name='short message', blank=True)),
                ('type', models.CharField(default=b'tempban', max_length=10, verbose_name='type', choices=[(b'permban', b'permanent ban'), (b'tempban', b'temporary ban'), (b'whitelist', b'whitelist'), (b'tempwhite', b'tempwhite')])),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created_at')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='modified_at')),
            ],
            options={
                'verbose_name': 'blacklist item',
                'verbose_name_plural': 'blacklist',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Domain',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=40, verbose_name='name', validators=[firewall.fields.val_domain])),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created_at')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='modified_at')),
                ('ttl', models.IntegerField(default=600, verbose_name='ttl')),
                ('description', models.TextField(verbose_name='description', blank=True)),
                ('owner', models.ForeignKey(verbose_name='owner', to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EthernetDevice',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text='The name of network interface the gateway should serve this network on. For example eth2.', unique=True, max_length=20, verbose_name='interface')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created_at')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='modified_at')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Firewall',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=20, verbose_name='name')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text='The name of the group.', unique=True, max_length=20, verbose_name='name')),
                ('description', models.TextField(help_text='Description of the group.', verbose_name='description', blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='modified at')),
                ('owner', models.ForeignKey(verbose_name='owner', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Host',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('hostname', models.CharField(help_text='The alphanumeric hostname of the host, the first part of the FQDN.', max_length=40, verbose_name='hostname', validators=[firewall.fields.val_alfanum])),
                ('normalized_hostname', common.models.HumanSortField(default=b'', max_length=80, monitor=b'hostname', blank=True)),
                ('reverse', models.CharField(validators=[firewall.fields.val_domain], max_length=40, blank=True, help_text='The fully qualified reverse hostname of the host, if different than hostname.domain.', null=True, verbose_name='reverse')),
                ('mac', firewall.fields.MACAddressField(help_text='The MAC (Ethernet) address of the network interface. For example: 99:AA:BB:CC:DD:EE.', unique=True, max_length=17, verbose_name='MAC address')),
                ('ipv4', firewall.fields.IPAddressField(help_text='The real IPv4 address of the host, for example 10.5.1.34.', unique=True, max_length=100, verbose_name='IPv4 address')),
                ('external_ipv4', firewall.fields.IPAddressField(help_text='The public IPv4 address of the host on the wide area network, if different.', max_length=100, null=True, verbose_name='WAN IPv4 address', blank=True)),
                ('ipv6', firewall.fields.IPAddressField(null=True, max_length=100, blank=True, help_text='The global IPv6 address of the host, for example 2001:db:88:200::10.', unique=True, verbose_name='IPv6 address')),
                ('shared_ip', models.BooleanField(default=False, help_text='If the given WAN IPv4 address is used by multiple hosts.', verbose_name='shared IP')),
                ('description', models.TextField(help_text='What is this host for, what kind of machine is it.', verbose_name='description', blank=True)),
                ('comment', models.TextField(verbose_name='Notes', blank=True)),
                ('location', models.TextField(help_text='The physical location of the machine.', verbose_name='location', blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='modified at')),
                ('groups', models.ManyToManyField(help_text='Host groups the machine is part of.', to='firewall.Group', null=True, verbose_name='groups', blank=True)),
                ('owner', models.ForeignKey(verbose_name='owner', to=settings.AUTH_USER_MODEL, help_text='The person responsible for this host.')),
            ],
            options={
                'ordering': ('normalized_hostname', 'vlan'),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Record',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(blank=True, max_length=40, null=True, verbose_name='name', validators=[firewall.fields.val_domain_wildcard])),
                ('type', models.CharField(max_length=6, verbose_name='type', choices=[(b'A', b'A'), (b'CNAME', b'CNAME'), (b'AAAA', b'AAAA'), (b'MX', b'MX'), (b'NS', b'NS'), (b'PTR', b'PTR'), (b'TXT', b'TXT')])),
                ('address', models.CharField(max_length=400, verbose_name='address')),
                ('ttl', models.IntegerField(default=600, verbose_name='ttl')),
                ('description', models.TextField(verbose_name='description', blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created_at')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='modified_at')),
                ('domain', models.ForeignKey(verbose_name='domain', to='firewall.Domain')),
                ('host', models.ForeignKey(verbose_name='host', blank=True, to='firewall.Host', null=True)),
                ('owner', models.ForeignKey(verbose_name='owner', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('domain', 'name'),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Rule',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('direction', models.CharField(help_text='If the rule matches egress or ingress packets.', max_length=3, verbose_name='direction', choices=[(b'out', 'out'), (b'in', 'in')])),
                ('description', models.TextField(help_text='Why is the rule needed, or how does it work.', verbose_name='description', blank=True)),
                ('dport', models.IntegerField(blank=True, help_text='Destination port number of packets that match.', null=True, verbose_name='dest. port', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(65535)])),
                ('sport', models.IntegerField(blank=True, help_text='Source port number of packets that match.', null=True, verbose_name='source port', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(65535)])),
                ('weight', models.IntegerField(default=30000, help_text='Rule weight', verbose_name='weight', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(65535)])),
                ('proto', models.CharField(choices=[(b'tcp', b'tcp'), (b'udp', b'udp'), (b'icmp', b'icmp')], max_length=10, blank=True, help_text='Protocol of packets that match.', null=True, verbose_name='protocol')),
                ('extra', models.TextField(help_text='Additional arguments passed literally to the iptables-rule.', verbose_name='extra arguments', blank=True)),
                ('action', models.CharField(default=b'drop', help_text='Accept, drop or ignore the matching packets.', max_length=10, verbose_name='action', choices=[(b'accept', 'accept'), (b'drop', 'drop'), (b'ignore', 'ignore')])),
                ('nat', models.BooleanField(default=False, help_text='If network address translation should be done.', verbose_name='NAT')),
                ('nat_external_port', models.IntegerField(blank=True, help_text='Rewrite destination port number to this if NAT is needed.', null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(65535)])),
                ('nat_external_ipv4', firewall.fields.IPAddressField(max_length=100, null=True, verbose_name='external IPv4 address', blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='modified at')),
                ('firewall', models.ForeignKey(related_name='rules', blank=True, to='firewall.Firewall', help_text='Firewall the rule applies to (if type is firewall).', null=True, verbose_name='firewall')),
            ],
            options={
                'ordering': ('direction', 'proto', 'sport', 'dport', 'nat_external_port', 'host'),
                'verbose_name': 'rule',
                'verbose_name_plural': 'rules',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SwitchPort',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('description', models.TextField(verbose_name='description', blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created_at')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='modified_at')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Vlan',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('vid', models.IntegerField(help_text='The vlan ID of the subnet.', unique=True, verbose_name='VID', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(4095)])),
                ('name', models.CharField(help_text='The short name of the subnet.', unique=True, max_length=20, verbose_name='Name', validators=[firewall.fields.val_alfanum])),
                ('network4', firewall.fields.IPNetworkField(help_text='The IPv4 address and the prefix length of the gateway. Recommended value is the last valid address of the subnet, for example 10.4.255.254/16 for 10.4.0.0/16.', max_length=100, verbose_name='IPv4 address/prefix')),
                ('host_ipv6_prefixlen', models.IntegerField(default=112, help_text='The prefix length of the subnet assigned to a host. For example /112 = 65536 addresses/host.', verbose_name='IPv6 prefixlen/host', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(128)])),
                ('network6', firewall.fields.IPNetworkField(help_text='The IPv6 address and the prefix length of the gateway.', max_length=100, null=True, verbose_name='IPv6 address/prefix', blank=True)),
                ('snat_ip', models.GenericIPAddressField(protocol=b'ipv4', blank=True, help_text='Common IPv4 address used for address translation of connections to the networks selected below (typically to the internet).', null=True, verbose_name='NAT IP address')),
                ('network_type', models.CharField(default=b'portforward', max_length=20, verbose_name='network type', choices=[(b'public', 'public'), (b'portforward', 'portforward')])),
                ('managed', models.BooleanField(default=True, verbose_name='managed')),
                ('description', models.TextField(help_text='Description of the goals and elements of the vlan network.', verbose_name='description', blank=True)),
                ('comment', models.TextField(help_text='Notes, comments about the network', verbose_name='comment', blank=True)),
                ('reverse_domain', models.TextField(default=b'%(d)d.%(c)d.%(b)d.%(a)d.in-addr.arpa', help_text='Template of the IPv4 reverse domain name that should be generated for each host. The template should contain four tokens: "%(a)d", "%(b)d", "%(c)d", and "%(d)d", representing the four bytes of the address, respectively, in decimal notation. For example, the template for the standard reverse address is: "%(d)d.%(c)d.%(b)d.%(a)d.in-addr.arpa".', verbose_name='reverse domain', validators=[firewall.fields.val_reverse_domain])),
                ('ipv6_template', models.TextField(default=b'2001:738:2001:4031:%(b)d:%(c)d:%(d)d:0', verbose_name='ipv6 template', validators=[firewall.fields.val_ipv6_template])),
                ('dhcp_pool', models.TextField(help_text='The address range of the DHCP pool: empty for no DHCP service, "manual" for no DHCP pool, or the first and last address of the range separated by a space.', verbose_name='DHCP pool', blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='modified at')),
                ('domain', models.ForeignKey(verbose_name='domain name', to='firewall.Domain', help_text='Domain name of the members of this network.')),
                ('owner', models.ForeignKey(verbose_name='owner', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('snat_to', models.ManyToManyField(help_text='Connections to these networks should be network address translated, i.e. their source address is rewritten to the value of NAT IP address.', to='firewall.Vlan', null=True, verbose_name='NAT to', blank=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='VlanGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text='The name of the group.', unique=True, max_length=20, verbose_name='name')),
                ('description', models.TextField(help_text='Description of the group.', verbose_name='description', blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='modified at')),
                ('owner', models.ForeignKey(verbose_name='owner', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('vlans', models.ManyToManyField(help_text='The vlans which are members of the group.', to='firewall.Vlan', null=True, verbose_name='vlans', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='switchport',
            name='tagged_vlans',
            field=models.ForeignKey(related_name='tagged_ports', verbose_name='tagged vlans', blank=True, to='firewall.VlanGroup', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='switchport',
            name='untagged_vlan',
            field=models.ForeignKey(related_name='untagged_ports', verbose_name='untagged vlan', to='firewall.Vlan'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='rule',
            name='foreign_network',
            field=models.ForeignKey(related_name='ForeignRules', verbose_name='foreign network', to='firewall.VlanGroup', help_text='The group of vlans the matching packet goes to (direction out) or from (in).'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='rule',
            name='host',
            field=models.ForeignKey(related_name='rules', blank=True, to='firewall.Host', help_text='Host the rule applies to (if type is host).', null=True, verbose_name='host'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='rule',
            name='hostgroup',
            field=models.ForeignKey(related_name='rules', blank=True, to='firewall.Group', help_text='Group of hosts the rule applies to (if type is host).', null=True, verbose_name='host group'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='rule',
            name='owner',
            field=models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, help_text='The user responsible for this rule.', null=True, verbose_name='owner'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='rule',
            name='vlan',
            field=models.ForeignKey(related_name='rules', blank=True, to='firewall.Vlan', help_text='Vlan the rule applies to (if type is vlan).', null=True, verbose_name='vlan'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='rule',
            name='vlangroup',
            field=models.ForeignKey(related_name='rules', blank=True, to='firewall.VlanGroup', help_text='Group of vlans the rule applies to (if type is vlan).', null=True, verbose_name='vlan group'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='host',
            name='vlan',
            field=models.ForeignKey(verbose_name='vlan', to='firewall.Vlan', help_text='Vlan network that the host is part of.'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='host',
            unique_together=set([('hostname', 'vlan')]),
        ),
        migrations.AddField(
            model_name='ethernetdevice',
            name='switch_port',
            field=models.ForeignKey(related_name='ethernet_devices', verbose_name='switch port', to='firewall.SwitchPort'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='blacklistitem',
            name='host',
            field=models.ForeignKey(verbose_name='host', blank=True, to='firewall.Host', null=True),
            preserve_default=True,
        ),
    ]
