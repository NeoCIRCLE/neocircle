# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('request', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='leasetype',
            name='lease',
            field=models.ForeignKey(verbose_name='Lease', to='vm.Lease'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='leasetype',
            name='name',
            field=models.CharField(max_length=25, verbose_name='Name'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='templateaccesstype',
            name='name',
            field=models.CharField(max_length=25, verbose_name='Name'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='templateaccesstype',
            name='templates',
            field=models.ManyToManyField(to='vm.InstanceTemplate', verbose_name='Templates'),
            preserve_default=True,
        ),
    ]
