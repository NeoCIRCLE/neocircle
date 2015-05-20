# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('firewall', '0004_auto_20150318_1317'),
    ]

    operations = [
        migrations.AlterField(
            model_name='host',
            name='groups',
            field=models.ManyToManyField(help_text='Host groups the machine is part of.', to='firewall.Group', verbose_name='groups', blank=True),
        ),
        migrations.AlterField(
            model_name='vlan',
            name='snat_to',
            field=models.ManyToManyField(help_text='Connections to these networks should be network address translated, i.e. their source address is rewritten to the value of NAT IP address.', to='firewall.Vlan', verbose_name='NAT to', blank=True),
        ),
        migrations.AlterField(
            model_name='vlangroup',
            name='vlans',
            field=models.ManyToManyField(help_text='The vlans which are members of the group.', to='firewall.Vlan', verbose_name='vlans', blank=True),
        ),
    ]
