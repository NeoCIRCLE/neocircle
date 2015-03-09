# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('firewall', '0002_auto_20150115_0021'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='blacklistitem',
            name='type',
        ),
        migrations.AddField(
            model_name='blacklistitem',
            name='expires_at',
            field=models.DateTimeField(default=None, null=True, verbose_name='expires at', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='blacklistitem',
            name='whitelisted',
            field=models.BooleanField(default=False, verbose_name='whitelisted'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='blacklistitem',
            name='ipv4',
            field=models.GenericIPAddressField(protocol=b'ipv4', unique=True, verbose_name=b'IPv4 address'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='blacklistitem',
            name='reason',
            field=models.TextField(null=True, verbose_name='reason', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='blacklistitem',
            name='snort_message',
            field=models.TextField(null=True, verbose_name='short message', blank=True),
            preserve_default=True,
        ),
    ]
