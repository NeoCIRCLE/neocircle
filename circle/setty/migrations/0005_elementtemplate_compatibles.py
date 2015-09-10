# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('setty', '0004_service_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='elementtemplate',
            name='compatibles',
            field=models.ManyToManyField(related_name='compatibles_rel_+', to='setty.ElementTemplate'),
        ),
    ]
