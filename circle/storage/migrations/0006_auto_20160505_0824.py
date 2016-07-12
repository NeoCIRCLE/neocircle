# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0005_auto_20160331_1823'),
    ]

    operations = [
        migrations.CreateModel(
            name='Endpoint',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=255, verbose_name='name')),
                ('address', models.CharField(max_length=1024, verbose_name='address')),
                ('port', models.IntegerField(null=True, verbose_name='port', blank=True)),
            ],
        ),
        migrations.RemoveField(
            model_name='datastore',
            name='hosts',
        ),
        migrations.DeleteModel(
            name='DataStoreHost',
        ),
        migrations.AddField(
            model_name='datastore',
            name='endpoints',
            field=models.ManyToManyField(to='storage.Endpoint', verbose_name='endpoints', blank=True),
        ),
    ]
