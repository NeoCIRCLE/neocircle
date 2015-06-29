# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import sizefield.models


class Migration(migrations.Migration):

    dependencies = [
        ('vm', '0002_interface_model'),
        ('storage', '0002_disk_bus'),
        ('request', '0003_auto_20150410_1917'),
    ]

    operations = [
        migrations.CreateModel(
            name='DiskResizeAction',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('size', sizefield.models.FileSizeField(default=None, null=True)),
                ('disk', models.ForeignKey(to='storage.Disk')),
                ('instance', models.ForeignKey(to='vm.Instance')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AlterField(
            model_name='request',
            name='type',
            field=models.CharField(max_length=10, choices=[(b'resource', 'resource request'), (b'lease', 'lease request'), (b'template', 'template access request'), (b'resize', 'disk resize request')]),
        ),
    ]
