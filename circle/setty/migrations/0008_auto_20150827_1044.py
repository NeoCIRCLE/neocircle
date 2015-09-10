# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import setty.storage


class Migration(migrations.Migration):

    dependencies = [
        ('setty', '0007_auto_20150827_1021'),
    ]

    operations = [
        migrations.AlterField(
            model_name='elementtemplate',
            name='logo',
            field=models.FileField(storage=setty.storage.OverwriteStorage(), upload_to=b'setty/'),
        ),
    ]
