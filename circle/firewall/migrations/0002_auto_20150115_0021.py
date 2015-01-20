# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import firewall.fields


class Migration(migrations.Migration):

    dependencies = [
        ('firewall', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vlan',
            name='ipv6_template',
            field=models.TextField(help_text='Template for translating IPv4 addresses to IPv6. Automatically generated hosts in dual-stack networks will get this address. The template can contain four tokens: "%(a)d", "%(b)d", "%(c)d", and "%(d)d", representing the four bytes of the IPv4 address, respectively, in decimal notation. Moreover you can use any standard printf format specification like %(a)02x to get the first byte as two hexadecimal digits. Usual choices for mapping 198.51.100.0/24 to 2001:0DB8:1:1::/64 would be "2001:db8:1:1:%(d)d::" and "2001:db8:1:1:%(d)02x00::".', blank=True, verbose_name='ipv6 template', validators=[firewall.fields.val_ipv6_template]),
            preserve_default=True,
        ),
    ]
