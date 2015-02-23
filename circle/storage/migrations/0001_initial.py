# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import model_utils.fields
import sizefield.models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DataStore',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100, verbose_name='name')),
                ('path', models.CharField(unique=True, max_length=200, verbose_name='path')),
                ('hostname', models.CharField(unique=True, max_length=40, verbose_name='hostname')),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'datastore',
                'verbose_name_plural': 'datastores',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Disk',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('name', models.CharField(max_length=100, verbose_name='name', blank=True)),
                ('filename', models.CharField(unique=True, max_length=256, verbose_name='filename')),
                ('type', models.CharField(max_length=10, choices=[('qcow2-norm', 'qcow2 normal'), ('qcow2-snap', 'qcow2 snapshot'), ('iso', 'iso'), ('raw-ro', 'raw read-only'), ('raw-rw', 'raw')])),
                ('size', sizefield.models.FileSizeField(default=None, null=True)),
                ('dev_num', models.CharField(default='a', max_length=1, verbose_name='device number')),
                ('destroyed', models.DateTimeField(default=None, null=True, blank=True)),
                ('is_ready', models.BooleanField(default=False)),
                ('base', models.ForeignKey(related_name='derivatives', blank=True, to='storage.Disk', null=True)),
                ('datastore', models.ForeignKey(verbose_name='datastore', to='storage.DataStore', help_text='The datastore that holds the disk.')),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'disk',
                'verbose_name_plural': 'disks',
                'permissions': (('create_empty_disk', 'Can create an empty disk.'), ('download_disk', 'Can download a disk.'), ('resize_disk', 'Can resize a disk.')),
            },
            bases=(models.Model,),
        ),
    ]
