# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('setty', '0018_auto_20160420_1728'),
    ]

    operations = [
        migrations.AlterField(
            model_name='servicenode',
            name='service',
            field=models.ForeignKey(related_name='node_service_id', default=None, to='setty.Service'),
        ),
    ]
