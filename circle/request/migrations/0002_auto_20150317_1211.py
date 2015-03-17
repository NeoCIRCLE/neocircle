# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('request', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='request',
            name='closed_by',
            field=models.ForeignKey(related_name='closed_by', to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='request',
            name='user',
            field=models.ForeignKey(related_name='user', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
    ]
