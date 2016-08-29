# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0002_disk_bus'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='disk',
            options={'ordering': ['name'], 'verbose_name': 'disk', 'verbose_name_plural': 'disks', 'permissions': (('create_empty_disk', 'Can create an empty disk.'), ('download_disk', 'Can download a disk.'), ('resize_disk', 'Can resize a disk.'), ('create_snapshot', 'Can create snapshot'), ('remove_snapshot', 'Can remove snapshot'), ('revert_snapshot', 'Can revert snapshot'), ('view_snapshot', 'Can view snapshot'))},
        ),
    ]
