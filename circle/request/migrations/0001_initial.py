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
        ('vm', '0002_interface_model'),
    ]

    operations = [
        migrations.CreateModel(
            name='Request',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('status', models.CharField(default=b'UNSEEN', max_length=10, choices=[(b'UNSEEN', 'unseen'), (b'PENDING', 'pending'), (b'ACCEPTED', 'accepted'), (b'DECLINED', 'declined')])),
                ('type', models.CharField(max_length=10, choices=[(b'resource', 'resource request'), (b'lease', 'lease request'), (b'template', 'template access')])),
                ('reason', models.TextField(help_text=b'szia')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RequestAction',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ExtendLeaseAction',
            fields=[
                ('requestaction_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='request.RequestAction')),
                ('instance', models.ForeignKey(to='vm.Instance')),
            ],
            options={
            },
            bases=('request.requestaction',),
        ),
        migrations.CreateModel(
            name='RequestType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=25)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='LeaseType',
            fields=[
                ('requesttype_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='request.RequestType')),
                ('lease', models.ForeignKey(to='vm.Lease')),
            ],
            options={
            },
            bases=('request.requesttype',),
        ),
        migrations.CreateModel(
            name='ResourceChangeAction',
            fields=[
                ('requestaction_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='request.RequestAction')),
                ('num_cores', models.IntegerField(help_text='Number of virtual CPU cores available to the virtual machine.', verbose_name='number of cores', validators=[django.core.validators.MinValueValidator(0)])),
                ('ram_size', models.IntegerField(help_text='Mebibytes of memory.', verbose_name='RAM size', validators=[django.core.validators.MinValueValidator(0)])),
                ('priority', models.IntegerField(help_text='CPU priority.', verbose_name='priority', validators=[django.core.validators.MinValueValidator(0)])),
                ('instance', models.ForeignKey(to='vm.Instance')),
            ],
            options={
            },
            bases=('request.requestaction',),
        ),
        migrations.CreateModel(
            name='TemplateAccessAction',
            fields=[
                ('requestaction_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='request.RequestAction')),
                ('level', models.CharField(default=b'user', max_length=10, choices=[(b'user', 'user'), (b'operator', 'operator')])),
            ],
            options={
            },
            bases=('request.requestaction',),
        ),
        migrations.CreateModel(
            name='TemplateAccessType',
            fields=[
                ('requesttype_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='request.RequestType')),
                ('templates', models.ManyToManyField(to='vm.InstanceTemplate')),
            ],
            options={
            },
            bases=('request.requesttype',),
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
            model_name='request',
            name='action',
            field=models.ForeignKey(to='request.RequestAction'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='request',
            name='user',
            field=models.ForeignKey(verbose_name='user', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='extendleaseaction',
            name='lease_type',
            field=models.ForeignKey(to='request.LeaseType'),
            preserve_default=True,
        ),
    ]
