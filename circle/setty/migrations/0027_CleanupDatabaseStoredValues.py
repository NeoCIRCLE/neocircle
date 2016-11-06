# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('setty', '0026_WordPressMemberChange'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='databasenode',
            name='adminUserName',
        ),
        migrations.RemoveField(
            model_name='databasenode',
            name='listeningPort',
        ),
        migrations.RemoveField(
            model_name='nginxnode',
            name='worker_connections',
        ),
        migrations.RemoveField(
            model_name='servicenode',
            name='config_file',
        ),
        migrations.RemoveField(
            model_name='webservernode',
            name='listeningPort',
        ),
        migrations.RemoveField(
            model_name='webservernode',
            name='useSSL',
        ),
        migrations.RemoveField(
            model_name='wordpressnode',
            name='databaseHost',
        ),
    ]
