# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0005_profile_two_factor_secret'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='org_id',
            field=models.CharField(help_text='Unique identifier of the person, e.g. a student number.', max_length=255, unique=True, null=True, blank=True),
        ),
    ]
