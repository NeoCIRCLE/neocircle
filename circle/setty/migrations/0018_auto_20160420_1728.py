# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('setty', '0017_auto_20160320_1828'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='servicenode',
            name='machine',
        ),
        migrations.AddField(
            model_name='servicenode',
            name='service',
            field=models.ForeignKey(default=None, to='setty.Service'),
        ),
    ]
