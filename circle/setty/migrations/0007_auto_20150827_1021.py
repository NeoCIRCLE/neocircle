# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('setty', '0006_auto_20150827_1017'),
    ]

    operations = [
        migrations.AlterField(
            model_name='elementtemplate',
            name='logo',
            field=models.FileField(upload_to=b'setty/'),
        ),
    ]