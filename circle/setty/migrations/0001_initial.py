# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import taggit.managers


class Migration(migrations.Migration):

    dependencies = [
        ('taggit', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Element',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('parameters', models.TextField()),
                ('displayId', models.TextField()),
                ('pos_x', models.PositiveSmallIntegerField()),
                ('pos_y', models.PositiveSmallIntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='ElementConnection',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('source_endpoint', models.TextField()),
                ('target_endpoint', models.TextField()),
                ('parameters', models.TextField()),
                ('source', models.ForeignKey(related_name='source', to='setty.Element')),
                ('target', models.ForeignKey(related_name='target', to='setty.Element')),
            ],
        ),
        migrations.CreateModel(
            name='ElementTemplate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('logo', models.FileField(upload_to=b'')),
                ('parameters', models.TextField()),
                ('tags', taggit.managers.TaggableManager(to='taggit.Tag', through='taggit.TaggedItem', blank=True, help_text='A comma-separated list of tags.', verbose_name='tags')),
            ],
        ),
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.TextField(verbose_name=b'Name')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='element',
            name='parent',
            field=models.ForeignKey(to='setty.ElementTemplate'),
        ),
        migrations.AddField(
            model_name='element',
            name='workspace',
            field=models.ForeignKey(to='setty.Service'),
        ),
    ]
