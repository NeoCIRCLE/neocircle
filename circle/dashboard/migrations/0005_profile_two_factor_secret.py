# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0004_profile_desktop_notifications'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='two_factor_secret',
            field=models.CharField(max_length=32, null=True, verbose_name='two factor secret key', blank=True),
        ),
    ]
