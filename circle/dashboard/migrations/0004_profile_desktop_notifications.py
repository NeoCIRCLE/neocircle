# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0003_message'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='desktop_notifications',
            field=models.BooleanField(default=False, help_text='Whether user wants to get desktop notification when an activity has finished and the window is not in focus.', verbose_name='Desktop notifications'),
        ),
    ]
