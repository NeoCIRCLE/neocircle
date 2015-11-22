# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0002_disk_bus'),
    ]

    operations = [
        migrations.CreateModel(
            name='DataStoreHost',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('address', models.CharField(max_length=1024, verbose_name='address')),
                ('port', models.IntegerField(null=True, verbose_name='port')),
            ],
        ),
        migrations.AddField(
            model_name='datastore',
            name='ceph_user',
            field=models.CharField(max_length=255, null=True, verbose_name='Ceph username'),
        ),
        migrations.AddField(
            model_name='datastore',
            name='secret_uuid',
            field=models.CharField(max_length=255, null=True, verbose_name='uuid of secret'),
        ),
        migrations.AddField(
            model_name='datastore',
            name='type',
            field=models.CharField(default='file', max_length=10, verbose_name='type', choices=[('file', 'filesystem'), ('ceph_block', 'Ceph block device')]),
        ),
        migrations.AlterField(
            model_name='datastore',
            name='hostname',
            field=models.CharField(max_length=40, verbose_name='hostname'),
        ),
        migrations.AlterField(
            model_name='disk',
            name='type',
            field=models.CharField(max_length=10, choices=[('qcow2-norm', 'qcow2 normal'), ('qcow2-snap', 'qcow2 snapshot'), ('ceph-norm', 'Ceph block normal'), ('ceph-snap', 'Ceph block snapshot'), ('iso', 'iso'), ('raw-ro', 'raw read-only'), ('raw-rw', 'raw')]),
        ),
        migrations.AddField(
            model_name='datastore',
            name='hosts',
            field=models.ManyToManyField(to='storage.DataStoreHost', verbose_name='hosts'),
        ),
    ]
