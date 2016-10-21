# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('setty', '0024_AddApacheAndWordpress'),
    ]

    operations = [
        migrations.CreateModel(
            name='DatabaseNode',
            fields=[
                ('servicenode_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='setty.ServiceNode')),
                ('adminUserName', models.CharField(max_length=50)),
                ('adminPassword', models.CharField(max_length=50)),
                ('listeningPort', models.PositiveIntegerField()),
            ],
            options={
                'abstract': False,
            },
            bases=('setty.servicenode',),
        ),
        migrations.CreateModel(
            name='MySQLNode',
            fields=[
                ('databasenode_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='setty.DatabaseNode')),
            ],
            options={
                'abstract': False,
            },
            bases=('setty.databasenode',),
        ),
        migrations.CreateModel(
            name='PostgreSQLNode',
            fields=[
                ('databasenode_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='setty.DatabaseNode')),
            ],
            options={
                'abstract': False,
            },
            bases=('setty.databasenode',),
        ),
    ]
