# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0006_auto_20160505_0824'),
    ]

    operations = [
        migrations.AddField(
            model_name='datastore',
            name='destroyed',
            field=models.DateTimeField(default=None, null=True, blank=True),
        ),
    ]
