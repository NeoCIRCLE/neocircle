# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('setty', '0002_elementtemplate_description'),
    ]

    operations = [
        migrations.RenameField(
            model_name='element',
            old_name='displayId',
            new_name='display_id',
        ),
        migrations.RenameField(
            model_name='element',
            old_name='workspace',
            new_name='service',
        ),
        migrations.RemoveField(
            model_name='element',
            name='parent',
        ),
    ]
