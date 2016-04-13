# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0005_auto_20160331_1823'),
        ('vm', '0002_interface_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='instance',
            name='datastore',
            field=models.ForeignKey(default=1, verbose_name='Data store', to='storage.DataStore', help_text="The target of VM's dump."),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='instancetemplate',
            name='datastore',
            field=models.ForeignKey(default=1, verbose_name='Data store', to='storage.DataStore', help_text="The target of VM's dump."),
            preserve_default=False,
        ),
    ]
