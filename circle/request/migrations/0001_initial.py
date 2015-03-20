# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
from django.conf import settings
import model_utils.fields
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0001_initial'),
        ('vm', '0002_interface_model'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExtendLeaseAction',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('instance', models.ForeignKey(to='vm.Instance')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='LeaseType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=25)),
                ('lease', models.ForeignKey(to='vm.Lease')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Request',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('status', models.CharField(default=b'PENDING', max_length=10, choices=[(b'PENDING', 'pending'), (b'ACCEPTED', 'accepted'), (b'DECLINED', 'declined')])),
                ('type', models.CharField(max_length=10, choices=[(b'resource', 'resource request'), (b'lease', 'lease request'), (b'template', 'template access')])),
                ('message', models.TextField(verbose_name='Message')),
                ('reason', models.TextField(verbose_name='Reason')),
                ('object_id', models.IntegerField()),
                ('closed_by', models.ForeignKey(related_name='closed_by', to=settings.AUTH_USER_MODEL, null=True)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType')),
                ('user', models.ForeignKey(related_name='user', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ResourceChangeAction',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('num_cores', models.IntegerField(help_text='Number of virtual CPU cores available to the virtual machine.', verbose_name='number of cores', validators=[django.core.validators.MinValueValidator(0)])),
                ('ram_size', models.IntegerField(help_text='Mebibytes of memory.', verbose_name='RAM size', validators=[django.core.validators.MinValueValidator(0)])),
                ('priority', models.IntegerField(help_text='CPU priority.', verbose_name='priority', validators=[django.core.validators.MinValueValidator(0)])),
                ('instance', models.ForeignKey(to='vm.Instance')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TemplateAccessAction',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('level', models.CharField(default=b'user', max_length=10, choices=[(b'user', 'user'), (b'operator', 'operator')])),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TemplateAccessType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=25)),
                ('templates', models.ManyToManyField(to='vm.InstanceTemplate')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='templateaccessaction',
            name='template_type',
            field=models.ForeignKey(to='request.TemplateAccessType'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='templateaccessaction',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='extendleaseaction',
            name='lease_type',
            field=models.ForeignKey(to='request.LeaseType'),
            preserve_default=True,
        ),
    ]
