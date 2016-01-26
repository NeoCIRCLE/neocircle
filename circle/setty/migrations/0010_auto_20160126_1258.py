# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('setty', '0009_element_anchors'),
    ]

    operations = [
        migrations.AlterField(
            model_name='element',
            name='pos_x',
            field=models.FloatField(),
        ),
        migrations.AlterField(
            model_name='element',
            name='pos_y',
            field=models.FloatField(),
        ),
    ]
