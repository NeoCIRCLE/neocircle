# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Level',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50, verbose_name=b'name')),
                ('codename', models.CharField(max_length=100, verbose_name=b'codename')),
                ('weight', models.IntegerField(null=True, verbose_name=b'weight')),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ObjectLevel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_id', models.IntegerField()),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType')),
                ('groups', models.ManyToManyField(to='auth.Group')),
                ('level', models.ForeignKey(to='acl.Level')),
                ('users', models.ManyToManyField(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='objectlevel',
            unique_together=set([('content_type', 'object_id', 'level')]),
        ),
        migrations.AlterUniqueTogether(
            name='level',
            unique_together=set([('content_type', 'codename')]),
        ),
    ]
