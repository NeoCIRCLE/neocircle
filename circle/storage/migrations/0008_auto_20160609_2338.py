# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0007_datastore_destroyed'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='datastore',
            name='secret_uuid',
        ),
        migrations.AddField(
            model_name='datastore',
            name='secret',
            field=models.CharField(max_length=255, null=True, verbose_name='secret key', blank=True),
        ),
    ]
