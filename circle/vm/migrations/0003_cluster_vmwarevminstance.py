# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import model_utils.fields
import common.operations
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('vm', '0002_interface_model'),
    ]

    operations = [
        migrations.CreateModel(
            name='Cluster',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('name', models.CharField(help_text='Human readable name of cluster.', unique=True, max_length=50, verbose_name='name')),
                ('address', models.CharField(help_text='The address of the vCenter.', max_length=200, verbose_name='address')),
                ('username', models.CharField(default='', help_text='The username used for the connection.', max_length=200, verbose_name='username')),
                ('password', models.CharField(default='', help_text='The password used for the connection.', max_length=200, verbose_name='password')),
            ],
            options={
                'db_table': 'vm_cluster',
            },
            bases=(common.operations.OperatedMixin, models.Model),
        ),
        migrations.CreateModel(
            name='VMwareVMInstance',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('name', models.CharField(help_text='The name of the virtual machine.', unique=True, max_length=50, verbose_name='name')),
                ('instanceUUID', models.CharField(help_text='A unique identifier of the VM.', unique=True, max_length=200, verbose_name='instanceUUID')),
                ('time_of_expiration', models.DateTimeField(default=None, help_text='The time, when the virtual machine will expire.', null=True, verbose_name='time of expiration', blank=True)),
                ('operating_system', models.CharField(help_text='The OS of the VM.', unique=True, max_length=200, verbose_name='operating system')),
                ('cpu_cores', models.IntegerField(help_text='The number of CPU cores in the VM.')),
                ('memory_size', models.IntegerField(help_text='The amount of memory (MB) in the VM.')),
                ('cluster', models.ForeignKey(to='vm.Cluster')),
                ('owner', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'vm_vmware_vminstance',
                'verbose_name': 'VMware virtual machine instance',
            },
            bases=(common.operations.OperatedMixin, models.Model),
        ),
    ]
