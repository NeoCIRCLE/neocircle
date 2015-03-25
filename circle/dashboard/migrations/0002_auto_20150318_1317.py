# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='connectcommand',
            options={'ordering': ('id',)},
        ),
        migrations.AlterModelOptions(
            name='futuremember',
            options={'ordering': ('id',)},
        ),
        migrations.AlterModelOptions(
            name='groupprofile',
            options={'ordering': ('id',)},
        ),
        migrations.AlterModelOptions(
            name='profile',
            options={'ordering': ('id',), 'permissions': (('use_autocomplete', 'Can use autocomplete.'),)},
        ),
    ]
