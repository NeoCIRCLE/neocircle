# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('setty', '0019_auto_20160420_2043'),
    ]

    operations = [
        migrations.AlterField(
            model_name='servicenode',
            name='service',
            field=models.ForeignKey(default=None, to='setty.Service'),
        ),
    ]
