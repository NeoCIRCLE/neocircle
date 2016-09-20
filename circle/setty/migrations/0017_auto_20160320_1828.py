# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import setty.storage


class Migration(migrations.Migration):

    dependencies = [
        ('setty', '0016_auto_20160320_1753'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='nginxnode',
            name='servicenode_ptr',
        ),
        migrations.AddField(
            model_name='nginxnode',
            name='webservernode_ptr',
            field=models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, default=None, serialize=False, to='setty.WebServerNode'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='elementtemplate',
            name='logo',
            field=models.FileField(storage=setty.storage.OverwriteStorage(), upload_to=b'setty/'),
        ),
    ]
