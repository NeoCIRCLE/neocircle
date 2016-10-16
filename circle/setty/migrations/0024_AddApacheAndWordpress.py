# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('setty', '0023_drop_parameters_from_elementconnection'),
    ]

    operations = [
        migrations.CreateModel(
            name='ApacheNode',
            fields=[
                ('webservernode_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='setty.WebServerNode')),
            ],
            options={
                'abstract': False,
            },
            bases=('setty.webservernode',),
        ),
        migrations.CreateModel(
            name='WordpressNode',
            fields=[
                ('servicenode_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='setty.ServiceNode')),
                ('databaseListeningPort', models.PositiveIntegerField()),
                ('databaseHost', models.TextField()),
                ('databaseUser', models.TextField()),
                ('databasePass', models.TextField()),
                ('adminUsername', models.TextField()),
                ('adminPassword', models.TextField()),
                ('adminEmail', models.TextField()),
                ('siteTitle', models.TextField()),
                ('siteUrl', models.TextField()),
            ],
            options={
                'abstract': False,
            },
            bases=('setty.servicenode',),
        ),
        migrations.RemoveField(
            model_name='machine',
            name='config_file',
        ),
    ]
