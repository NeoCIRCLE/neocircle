# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('request', '0002_auto_20150407_1117'),
    ]

    operations = [
        migrations.AlterField(
            model_name='leasetype',
            name='name',
            field=models.CharField(max_length=100, verbose_name='Name'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='request',
            name='type',
            field=models.CharField(max_length=10, choices=[(b'resource', 'resource request'), (b'lease', 'lease request'), (b'template', 'template access request')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='templateaccesstype',
            name='name',
            field=models.CharField(max_length=100, verbose_name='Name'),
            preserve_default=True,
        ),
    ]
