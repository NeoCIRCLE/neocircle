# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('request', '0002_auto_20150317_1211'),
    ]

    operations = [
        migrations.AlterField(
            model_name='request',
            name='reason',
            field=models.TextField(verbose_name='Reason'),
            preserve_default=True,
        ),
    ]
