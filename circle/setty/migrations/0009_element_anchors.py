# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('setty', '0008_auto_20150827_1044'),
    ]

    operations = [
        migrations.AddField(
            model_name='element',
            name='anchors',
            field=models.PositiveSmallIntegerField(default=0),
            preserve_default=False,
        ),
    ]
