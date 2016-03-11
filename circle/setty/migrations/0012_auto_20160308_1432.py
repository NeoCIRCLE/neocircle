# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('setty', '0011_auto_20160308_1432'),
    ]

    operations = [
        migrations.RenameField(
            model_name='element',
            old_name='pos_top',
            new_name='position_top',
        ),
    ]
