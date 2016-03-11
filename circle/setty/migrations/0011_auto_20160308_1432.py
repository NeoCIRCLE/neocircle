# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('setty', '0010_auto_20160126_1258'),
    ]

    operations = [
        migrations.RenameField(
            model_name='element',
            old_name='anchors',
            new_name='anchor_number',
        ),
        migrations.RenameField(
            model_name='element',
            old_name='pos_x',
            new_name='pos_top',
        ),
        migrations.RenameField(
            model_name='element',
            old_name='pos_y',
            new_name='position_left',
        ),
    ]
