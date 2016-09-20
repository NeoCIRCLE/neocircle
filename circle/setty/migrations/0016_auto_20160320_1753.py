# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import setty.storage


class Migration(migrations.Migration):

    dependencies = [
        ('setty', '0015_allow_blank_elementcategory_parent'),
    ]

    operations = [
        migrations.AddField(
            model_name='elementtemplate',
            name='prototype',
            field=models.TextField(default=b'<SYNTAX ERROR>'),
        ),
        migrations.AlterField(
            model_name='elementtemplate',
            name='compatibles',
            field=models.ManyToManyField(related_name='compatibles_rel_+', to='setty.ElementTemplate', blank=True),
        ),
        migrations.AlterField(
            model_name='elementtemplate',
            name='logo',
            field=models.FileField(storage=setty.storage.OverwriteStorage(), upload_to=b'setty/', blank=True),
        ),
    ]
