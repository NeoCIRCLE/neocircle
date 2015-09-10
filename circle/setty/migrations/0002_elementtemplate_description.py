# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('setty', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='elementtemplate',
            name='description',
            field=models.TextField(default=datetime.datetime(2015, 6, 30, 7, 23, 44, 511713, tzinfo=utc)),
            preserve_default=False,
        ),
    ]
