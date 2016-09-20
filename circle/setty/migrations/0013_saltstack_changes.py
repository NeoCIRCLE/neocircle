# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import setty.storage


class Migration(migrations.Migration):

    dependencies = [
        ('setty', '0012_auto_20160308_1432'),
    ]

    operations = [
        migrations.CreateModel(
            name='ElementCategory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('parent_category', models.ForeignKey(to='setty.ElementCategory', null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Machine',
            fields=[
                ('element_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='setty.Element')),
                ('hostname', models.TextField()),
                ('alias', models.CharField(max_length=50)),
                ('config_file', models.FileField(default=None, storage=setty.storage.OverwriteStorage(), upload_to=b'setty/machine_configs/')),
                ('description', models.TextField(default=b'')),
                ('status', models.CharField(max_length=1, choices=[(1, b'Running'), (2, b'Unreachable')])),
            ],
            options={
                'abstract': False,
            },
            bases=('setty.element',),
        ),
        migrations.CreateModel(
            name='ServiceNode',
            fields=[
                ('element_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='setty.Element')),
                ('name', models.CharField(max_length=50)),
                ('config_file', models.FileField(default=None, storage=setty.storage.OverwriteStorage(), upload_to=b'setty/node_configs/')),
                ('description', models.TextField(default=b'')),
                ('machine', models.ForeignKey(to='setty.Machine')),
            ],
            bases=('setty.element',),
        ),
        migrations.RemoveField(
            model_name='element',
            name='parameters',
        ),
        migrations.RemoveField(
            model_name='element',
            name='service',
        ),
        migrations.RemoveField(
            model_name='elementtemplate',
            name='parameters',
        ),
        migrations.AlterField(
            model_name='service',
            name='status',
            field=models.CharField(default=1, max_length=1, choices=[(1, b'Draft'), (2, b'Deployed')]),
        ),
        migrations.AddField(
            model_name='machine',
            name='service',
            field=models.ForeignKey(related_name='service_id', to='setty.Service'),
        ),
        migrations.AddField(
            model_name='elementtemplate',
            name='category',
            field=models.ForeignKey(to='setty.ElementCategory', null=True),
        ),
    ]
