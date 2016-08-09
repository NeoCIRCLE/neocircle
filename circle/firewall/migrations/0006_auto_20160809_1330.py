# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('firewall', '0005_auto_20150520_2250'),
    ]

    operations = [
        migrations.AddField(
            model_name='rule',
            name='dport_end',
            field=models.IntegerField(blank=True, help_text='End of the destination port range.', null=True, verbose_name='destination port end', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(65535)]),
        ),
        migrations.AddField(
            model_name='rule',
            name='sport_end',
            field=models.IntegerField(blank=True, help_text='End of the source port range.', null=True, verbose_name='source port end', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(65535)]),
        ),
        migrations.AlterField(
            model_name='rule',
            name='dport',
            field=models.IntegerField(blank=True, help_text='Destination port number of packets that match. It can also be a range.', null=True, verbose_name='destination port', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(65535)]),
        ),
        migrations.AlterField(
            model_name='rule',
            name='sport',
            field=models.IntegerField(blank=True, help_text='Source port number of packets that match. It can also be a range.', null=True, verbose_name='source port', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(65535)]),
        ),
    ]
