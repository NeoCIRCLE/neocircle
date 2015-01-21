# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import dashboard.validators
import dashboard.models
import model_utils.fields
import sizefield.models
import jsonfield.fields
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('vm', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConnectCommand',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('access_method', models.CharField(help_text='Type of the remote access method.', max_length=10, verbose_name='access method', choices=[('nx', 'NX'), ('rdp', 'RDP'), ('ssh', 'SSH')])),
                ('name', models.CharField(help_text='Name of your custom command.', max_length=b'128', verbose_name='name')),
                ('template', models.CharField(validators=[dashboard.validators.connect_command_template_validator], max_length=256, blank=True, help_text='Template for connection command string. Available parameters are: username, password, host, port.', null=True, verbose_name='command template')),
                ('user', models.ForeignKey(related_name='command_set', to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Favourite',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('instance', models.ForeignKey(to='vm.Instance')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FutureMember',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('org_id', models.CharField(help_text='Unique identifier of the person, e.g. a student number.', max_length=64)),
                ('group', models.ForeignKey(to='auth.Group')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GroupProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('org_id', models.CharField(help_text='Unique identifier of the group at the organization.', max_length=64, unique=True, null=True, blank=True)),
                ('description', models.TextField(blank=True)),
                ('group', models.OneToOneField(to='auth.Group')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('status', model_utils.fields.StatusField(default=b'new', max_length=100, no_check_for_status=True, choices=[(b'new', 'new'), (b'delivered', 'delivered'), (b'read', 'read')])),
                ('subject_data', jsonfield.fields.JSONField(null=True)),
                ('message_data', jsonfield.fields.JSONField(null=True)),
                ('valid_until', models.DateTimeField(default=None, null=True)),
                ('to', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('preferred_language', models.CharField(default=b'en', max_length=32, verbose_name='preferred language', choices=[(b'en', 'English'), (b'hu', 'Hungarian')])),
                ('org_id', models.CharField(help_text='Unique identifier of the person, e.g. a student number.', max_length=64, unique=True, null=True, blank=True)),
                ('instance_limit', models.IntegerField(default=5)),
                ('use_gravatar', models.BooleanField(default=True, help_text='Whether to use email address as Gravatar profile image', verbose_name='Use Gravatar')),
                ('email_notifications', models.BooleanField(default=True, help_text='Whether user wants to get digested email notifications.', verbose_name='Email notifications')),
                ('smb_password', models.CharField(default=dashboard.models.pwgen, help_text='Generated password for accessing store from virtual machines.', max_length=20, verbose_name='Samba password')),
                ('disk_quota', sizefield.models.FileSizeField(default=2147483648, help_text='Disk quota in mebibytes.', verbose_name='disk quota')),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'permissions': (('use_autocomplete', 'Can use autocomplete.'),),
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='futuremember',
            unique_together=set([('org_id', 'group')]),
        ),
    ]
