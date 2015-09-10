# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('setty', '0005_elementtemplate_compatibles'),
    ]

    operations = [
        migrations.AlterField(
            model_name='elementtemplate',
            name='logo',
            field=models.FileField(upload_to=b'/setty/static'),
        ),
    ]
