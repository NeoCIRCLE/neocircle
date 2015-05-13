# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0002_auto_20150318_1317'),
    ]

    operations = [
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('start', models.DateTimeField(null=True, verbose_name='start', blank=True)),
                ('end', models.DateTimeField(null=True, verbose_name='end', blank=True)),
                ('message', models.CharField(max_length=500, verbose_name='message')),
                ('effect', models.CharField(default=b'info', max_length=10, verbose_name='effect', choices=[(b'success', 'success'), (b'info', 'info'), (b'warning', 'warning'), (b'danger', 'danger')])),
                ('enabled', models.BooleanField(default=False, verbose_name='enabled')),
            ],
            options={
                'ordering': ['id'],
                'verbose_name': 'message',
                'verbose_name_plural': 'messages',
            },
            bases=(models.Model,),
        ),
    ]
