# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('setty', '0014_auto_20160320_1724'),
    ]

    operations = [
        migrations.AlterField(
            model_name='elementcategory',
            name='parent_category',
            field=models.ForeignKey(blank=True, to='setty.ElementCategory', null=True),
        ),
    ]
