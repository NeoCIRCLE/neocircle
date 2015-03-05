# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vm', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='interface',
            name='model',
            field=models.CharField(default='virtio', max_length=10, choices=[('virtio', 'virtio'), ('ne2k_pci', 'ne2k_pci'), ('pcnet', 'pcnet'), ('rtl8139', 'rtl8139'), ('e1000', 'e1000')]),
            preserve_default=True,
        ),
    ]
