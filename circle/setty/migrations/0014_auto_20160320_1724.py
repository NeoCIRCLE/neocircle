# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('setty', '0013_saltstack_changes'),
    ]

    operations = [
        migrations.CreateModel(
            name='NginxNode',
            fields=[
                ('servicenode_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='setty.ServiceNode')),
                ('worker_connections', models.PositiveIntegerField()),
            ],
            bases=('setty.servicenode',),
        ),
        migrations.CreateModel(
            name='WebServerNode',
            fields=[
                ('servicenode_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='setty.ServiceNode')),
                ('useSSL', models.BooleanField(default=False)),
                ('listeningPort', models.PositiveIntegerField()),
            ],
            bases=('setty.servicenode',),
        ),
        migrations.RemoveField(
            model_name='elementtemplate',
            name='tags',
        ),
    ]
