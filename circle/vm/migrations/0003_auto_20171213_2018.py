# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-12-13 20:18
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('vm', '0002_interface_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='node',
            name='cpu_weight',
            field=models.FloatField(default=1.0, help_text='Indicates the relative CPU power of this node.', verbose_name='CPU Weight'),
        ),
        migrations.AddField(
            model_name='node',
            name='ram_weight',
            field=models.FloatField(default=1.0, help_text='Indicates the relative RAM quantity of this node.', verbose_name='RAM Weight'),
        ),
        migrations.AddField(
            model_name='node',
            name='time_stamp',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, help_text='A timestamp for the node, used by the scheduler.', verbose_name='Last Scheduled Time Stamp'),
            preserve_default=False,
        ),
    ]
