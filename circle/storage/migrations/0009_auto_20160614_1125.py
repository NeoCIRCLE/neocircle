# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0008_auto_20160609_2338'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='datastore',
            name='endpoints',
        ),
        migrations.DeleteModel(
            name='Endpoint',
        ),
    ]
