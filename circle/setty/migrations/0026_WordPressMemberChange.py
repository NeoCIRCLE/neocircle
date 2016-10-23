# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('setty', '0025_AddDatabases'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='wordpressnode',
            name='databaseListeningPort',
        ),
        migrations.AddField(
            model_name='wordpressnode',
            name='databaseName',
            field=models.TextField(default=b''),
        ),
        migrations.AlterField(
            model_name='wordpressnode',
            name='adminEmail',
            field=models.TextField(default=b''),
        ),
        migrations.AlterField(
            model_name='wordpressnode',
            name='adminPassword',
            field=models.TextField(default=b''),
        ),
        migrations.AlterField(
            model_name='wordpressnode',
            name='adminUsername',
            field=models.TextField(default=b''),
        ),
        migrations.AlterField(
            model_name='wordpressnode',
            name='databaseHost',
            field=models.TextField(default=b''),
        ),
        migrations.AlterField(
            model_name='wordpressnode',
            name='databasePass',
            field=models.TextField(default=b''),
        ),
        migrations.AlterField(
            model_name='wordpressnode',
            name='databaseUser',
            field=models.TextField(default=b''),
        ),
        migrations.AlterField(
            model_name='wordpressnode',
            name='siteTitle',
            field=models.TextField(default=b''),
        ),
        migrations.AlterField(
            model_name='wordpressnode',
            name='siteUrl',
            field=models.TextField(default=b''),
        ),
    ]
