# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('setty', '0020_auto_20160420_2132'),
    ]

    operations = [
        migrations.AddField(
            model_name='element',
            name='real_type',
            field=models.ForeignKey(default=None, editable=False, to='contenttypes.ContentType'),
        ),
    ]
