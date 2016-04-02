# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import storage.models


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0004_auto_20151212_0402'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datastore',
            name='path',
            field=models.CharField(unique=True, max_length=200, verbose_name='path or poolname', validators=[storage.models.validate_ascii]),
        ),
        migrations.AlterField(
            model_name='datastore',
            name='secret_uuid',
            field=models.CharField(max_length=255, null=True, verbose_name='uuid of secret key', blank=True),
        ),
    ]
