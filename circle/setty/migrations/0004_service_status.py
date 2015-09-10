# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('setty', '0003_auto_20150701_1621'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='status',
            field=models.CharField(default=datetime.datetime(2015, 8, 6, 8, 43, 54, 868047, tzinfo=utc), max_length=50),
            preserve_default=False,
        ),
    ]
