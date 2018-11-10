# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0009_auto_20160614_1125'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='datastore',
            name='secret',
        ),
    ]
