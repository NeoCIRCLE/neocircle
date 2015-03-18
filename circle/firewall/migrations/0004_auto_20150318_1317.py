# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('firewall', '0003_auto_20150226_1927'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='blacklistitem',
            options={'ordering': ('id',), 'verbose_name': 'blacklist item', 'verbose_name_plural': 'blacklist items'},
        ),
        migrations.AlterModelOptions(
            name='domain',
            options={'ordering': ('id',), 'verbose_name': 'domain', 'verbose_name_plural': 'domains'},
        ),
        migrations.AlterModelOptions(
            name='ethernetdevice',
            options={'ordering': ('id',), 'verbose_name': 'ethernet device', 'verbose_name_plural': 'ethernet devices'},
        ),
        migrations.AlterModelOptions(
            name='firewall',
            options={'ordering': ('id',), 'verbose_name': 'firewall', 'verbose_name_plural': 'firewalls'},
        ),
        migrations.AlterModelOptions(
            name='group',
            options={'ordering': ('id',), 'verbose_name': 'host group', 'verbose_name_plural': 'host groups'},
        ),
        migrations.AlterModelOptions(
            name='record',
            options={'ordering': ('domain', 'name'), 'verbose_name': 'record', 'verbose_name_plural': 'records'},
        ),
        migrations.AlterModelOptions(
            name='switchport',
            options={'ordering': ('id',), 'verbose_name': 'switch port', 'verbose_name_plural': 'switch ports'},
        ),
        migrations.AlterModelOptions(
            name='vlan',
            options={'ordering': ('vid',), 'verbose_name': 'vlan', 'verbose_name_plural': 'vlans'},
        ),
        migrations.AlterModelOptions(
            name='vlangroup',
            options={'ordering': ('id',), 'verbose_name': 'vlan group', 'verbose_name_plural': 'vlan groups'},
        ),
    ]
