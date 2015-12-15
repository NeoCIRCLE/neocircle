# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import storage.models


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0003_auto_20151122_2104'),
    ]

    operations = [
        migrations.AddField(
            model_name='datastorehost',
            name='name',
            field=models.CharField(default='Monitor1', unique=True, max_length=255, verbose_name='name'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='datastore',
            name='path',
            field=models.CharField(unique=True, max_length=200, verbose_name='path', validators=[storage.models.validate_ascii]),
        ),
        migrations.AlterField(
            model_name='disk',
            name='filename',
            field=models.CharField(unique=True, max_length=256, verbose_name='filename', validators=[storage.models.validate_ascii]),
        ),
    ]
