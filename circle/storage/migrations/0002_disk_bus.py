# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='disk',
            name='bus',
            field=models.CharField(default=None, max_length=10, null=True, blank=True, choices=[('virtio', 'virtio'), ('ide', 'ide'), ('scsi', 'scsi')]),
            preserve_default=True,
        ),
    ]
