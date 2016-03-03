# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vm', '0002_interface_model'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='instance',
            options={'ordering': ('pk',), 'verbose_name': 'instance', 'verbose_name_plural': 'instances', 'permissions': (('access_console', 'Can access the graphical console of a VM.'), ('change_resources', 'Can change resources of a running VM.'), ('set_resources', 'Can change resources of a new VM.'), ('create_vm', 'Can create a new VM.'), ('redeploy', 'Can redeploy a VM.'), ('config_ports', 'Can configure port forwards.'), ('recover', 'Can recover a destroyed VM.'), ('emergency_change_state', 'Can change VM state to NOSTATE.'), ('toggle_boot_menu', 'Can turn on/off boot menu.'))},
        ),
    ]
