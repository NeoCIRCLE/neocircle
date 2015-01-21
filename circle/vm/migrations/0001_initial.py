# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import taggit.managers
import model_utils.fields
import jsonfield.fields
import common.operations
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
import common.models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('taggit', '0001_initial'),
        ('storage', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('firewall', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Instance',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('status', model_utils.fields.StatusField(default='NOSTATE', max_length=100, verbose_name='status', no_check_for_status=True, choices=[('NOSTATE', 'no state'), ('RUNNING', 'running'), ('STOPPED', 'stopped'), ('SUSPENDED', 'suspended'), ('ERROR', 'error'), ('PENDING', 'pending'), ('DESTROYED', 'destroyed')])),
                ('status_changed', model_utils.fields.MonitorField(default=django.utils.timezone.now, verbose_name='status changed', monitor='status')),
                ('num_cores', models.IntegerField(help_text='Number of virtual CPU cores available to the virtual machine.', verbose_name='number of cores', validators=[django.core.validators.MinValueValidator(0)])),
                ('ram_size', models.IntegerField(help_text='Mebibytes of memory.', verbose_name='RAM size', validators=[django.core.validators.MinValueValidator(0)])),
                ('max_ram_size', models.IntegerField(help_text='Upper memory size limit for balloning.', verbose_name='maximal RAM size', validators=[django.core.validators.MinValueValidator(0)])),
                ('arch', models.CharField(max_length=10, verbose_name='architecture', choices=[('x86_64', 'x86-64 (64 bit)'), ('i686', 'x86 (32 bit)')])),
                ('priority', models.IntegerField(help_text='CPU priority.', verbose_name='priority', validators=[django.core.validators.MinValueValidator(0)])),
                ('access_method', models.CharField(help_text='Primary remote access method.', max_length=10, verbose_name='access method', choices=[('nx', 'NX'), ('rdp', 'RDP'), ('ssh', 'SSH')])),
                ('boot_menu', models.BooleanField(default=False, help_text='Show boot device selection menu on boot.', verbose_name='boot menu')),
                ('raw_data', models.TextField(help_text='Additional libvirt domain parameters in XML format.', verbose_name='raw_data', blank=True)),
                ('system', models.TextField(help_text='Name of operating system in format like "Ubuntu 12.04 LTS Desktop amd64".', verbose_name='operating system')),
                ('has_agent', models.BooleanField(default=True, help_text='If the machine has agent installed, and the manager should wait for its start.', verbose_name='has agent')),
                ('name', models.CharField(help_text='Human readable name of instance.', max_length=100, verbose_name='name', blank=True)),
                ('description', models.TextField(verbose_name='description', blank=True)),
                ('pw', models.CharField(help_text='Original password of the instance.', max_length=20, verbose_name='password')),
                ('time_of_suspend', models.DateTimeField(default=None, help_text='Proposed time of automatic suspension.', null=True, verbose_name='time of suspend', blank=True)),
                ('time_of_delete', models.DateTimeField(default=None, help_text='Proposed time of automatic deletion.', null=True, verbose_name='time of delete', blank=True)),
                ('vnc_port', models.IntegerField(null=True, default=None, blank=True, help_text='TCP port where VNC console listens.', unique=True, verbose_name='vnc_port')),
                ('is_base', models.BooleanField(default=False)),
                ('destroyed_at', models.DateTimeField(help_text="The virtual machine's time of destruction.", null=True, blank=True)),
                ('disks', models.ManyToManyField(help_text='Set of mounted disks.', related_name='instance_set', verbose_name='disks', to='storage.Disk')),
            ],
            options={
                'ordering': ('pk',),
                'db_table': 'vm_instance',
                'verbose_name': 'instance',
                'verbose_name_plural': 'instances',
                'permissions': (('access_console', 'Can access the graphical console of a VM.'), ('change_resources', 'Can change resources of a running VM.'), ('set_resources', 'Can change resources of a new VM.'), ('create_vm', 'Can create a new VM.'), ('redeploy', 'Can redeploy a VM.'), ('config_ports', 'Can configure port forwards.'), ('recover', 'Can recover a destroyed VM.'), ('emergency_change_state', 'Can change VM state to NOSTATE.')),
            },
            bases=(common.operations.OperatedMixin, models.Model),
        ),
        migrations.CreateModel(
            name='InstanceActivity',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('activity_code', models.CharField(max_length=100, verbose_name='activity code')),
                ('readable_name_data', jsonfield.fields.JSONField(help_text='Human readable name of activity.', null=True, verbose_name='human readable name', blank=True)),
                ('task_uuid', models.CharField(null=True, max_length=50, blank=True, help_text='Celery task unique identifier.', unique=True, verbose_name='task_uuid')),
                ('started', models.DateTimeField(help_text='Time of activity initiation.', null=True, verbose_name='started at', blank=True)),
                ('finished', models.DateTimeField(help_text='Time of activity finalization.', null=True, verbose_name='finished at', blank=True)),
                ('succeeded', models.NullBooleanField(help_text='True, if the activity has finished successfully.')),
                ('result_data', jsonfield.fields.JSONField(help_text='Human readable result of activity.', null=True, verbose_name='result', blank=True)),
                ('resultant_state', models.CharField(max_length=20, null=True, blank=True)),
                ('interruptible', models.BooleanField(default=False, help_text='Other activities can interrupt this one.')),
                ('instance', models.ForeignKey(related_name='activity_log', verbose_name='instance', to='vm.Instance', help_text='Instance this activity works on.')),
                ('parent', models.ForeignKey(related_name='children', blank=True, to='vm.InstanceActivity', null=True)),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, help_text='The person who started this activity.', null=True, verbose_name='user')),
            ],
            options={
                'ordering': ['-finished', '-started', 'instance', '-id'],
                'db_table': 'vm_instanceactivity',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='InstanceTemplate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('num_cores', models.IntegerField(help_text='Number of virtual CPU cores available to the virtual machine.', verbose_name='number of cores', validators=[django.core.validators.MinValueValidator(0)])),
                ('ram_size', models.IntegerField(help_text='Mebibytes of memory.', verbose_name='RAM size', validators=[django.core.validators.MinValueValidator(0)])),
                ('max_ram_size', models.IntegerField(help_text='Upper memory size limit for balloning.', verbose_name='maximal RAM size', validators=[django.core.validators.MinValueValidator(0)])),
                ('arch', models.CharField(max_length=10, verbose_name='architecture', choices=[('x86_64', 'x86-64 (64 bit)'), ('i686', 'x86 (32 bit)')])),
                ('priority', models.IntegerField(help_text='CPU priority.', verbose_name='priority', validators=[django.core.validators.MinValueValidator(0)])),
                ('access_method', models.CharField(help_text='Primary remote access method.', max_length=10, verbose_name='access method', choices=[('nx', 'NX'), ('rdp', 'RDP'), ('ssh', 'SSH')])),
                ('boot_menu', models.BooleanField(default=False, help_text='Show boot device selection menu on boot.', verbose_name='boot menu')),
                ('raw_data', models.TextField(help_text='Additional libvirt domain parameters in XML format.', verbose_name='raw_data', blank=True)),
                ('system', models.TextField(help_text='Name of operating system in format like "Ubuntu 12.04 LTS Desktop amd64".', verbose_name='operating system')),
                ('has_agent', models.BooleanField(default=True, help_text='If the machine has agent installed, and the manager should wait for its start.', verbose_name='has agent')),
                ('name', models.CharField(help_text='Human readable name of template.', max_length=100, verbose_name='name')),
                ('description', models.TextField(verbose_name='description', blank=True)),
                ('disks', models.ManyToManyField(help_text='Disks which are to be mounted.', related_name='template_set', verbose_name='disks', to='storage.Disk')),
            ],
            options={
                'ordering': ('name',),
                'db_table': 'vm_instancetemplate',
                'verbose_name': 'template',
                'verbose_name_plural': 'templates',
                'permissions': (('create_template', 'Can create an instance template.'), ('create_base_template', 'Can create an instance template (base).'), ('change_template_resources', 'Can change resources of a template.')),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Interface',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('host', models.ForeignKey(verbose_name='host', blank=True, to='firewall.Host', null=True)),
                ('instance', models.ForeignKey(related_name='interface_set', verbose_name='instance', to='vm.Instance')),
                ('vlan', models.ForeignKey(related_name='vm_interface', verbose_name='vlan', to='firewall.Vlan')),
            ],
            options={
                'ordering': ('-vlan__managed',),
                'db_table': 'vm_interface',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='InterfaceTemplate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('managed', models.BooleanField(default=True, help_text='If a firewall host (i.e. IP address association) should be generated.', verbose_name='managed')),
                ('template', models.ForeignKey(related_name='interface_set', verbose_name='template', to='vm.InstanceTemplate', help_text='Template the interface template belongs to.')),
                ('vlan', models.ForeignKey(verbose_name='vlan', to='firewall.Vlan', help_text='Network the interface belongs to.')),
            ],
            options={
                'db_table': 'vm_interfacetemplate',
                'verbose_name': 'interface template',
                'verbose_name_plural': 'interface templates',
                'permissions': (),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Lease',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100, verbose_name='name')),
                ('suspend_interval_seconds', models.IntegerField(help_text='Number of seconds after the an instance is suspended.', null=True, verbose_name='suspend interval', blank=True)),
                ('delete_interval_seconds', models.IntegerField(help_text='Number of seconds after the an instance is deleted.', null=True, verbose_name='delete interval', blank=True)),
            ],
            options={
                'ordering': ['name'],
                'db_table': 'vm_lease',
                'permissions': (('create_leases', 'Can create new leases.'),),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='NamedBaseResourceConfig',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('num_cores', models.IntegerField(help_text='Number of virtual CPU cores available to the virtual machine.', verbose_name='number of cores', validators=[django.core.validators.MinValueValidator(0)])),
                ('ram_size', models.IntegerField(help_text='Mebibytes of memory.', verbose_name='RAM size', validators=[django.core.validators.MinValueValidator(0)])),
                ('max_ram_size', models.IntegerField(help_text='Upper memory size limit for balloning.', verbose_name='maximal RAM size', validators=[django.core.validators.MinValueValidator(0)])),
                ('arch', models.CharField(max_length=10, verbose_name='architecture', choices=[('x86_64', 'x86-64 (64 bit)'), ('i686', 'x86 (32 bit)')])),
                ('priority', models.IntegerField(help_text='CPU priority.', verbose_name='priority', validators=[django.core.validators.MinValueValidator(0)])),
                ('name', models.CharField(help_text='Name of base resource configuration.', unique=True, max_length=50, verbose_name='name')),
            ],
            options={
                'db_table': 'vm_namedbaseresourceconfig',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Node',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('name', models.CharField(help_text='Human readable name of node.', unique=True, max_length=50, verbose_name='name')),
                ('normalized_name', common.models.HumanSortField(default=b'', max_length=100, monitor='name', blank=True)),
                ('priority', models.IntegerField(help_text='Node usage priority.', verbose_name='priority')),
                ('enabled', models.BooleanField(default=False, help_text='Indicates whether the node can be used for hosting.', verbose_name='enabled')),
                ('schedule_enabled', models.BooleanField(default=False, help_text='Indicates whether a vm can be automatically scheduled to this node.', verbose_name='schedule enabled')),
                ('overcommit', models.FloatField(default=1.0, help_text='The ratio of total memory with to without overcommit.', verbose_name='overcommit ratio')),
                ('host', models.ForeignKey(verbose_name='host', to='firewall.Host', help_text='Host in firewall.')),
                ('tags', taggit.managers.TaggableManager(to='taggit.Tag', through='taggit.TaggedItem', blank=True, help_text='A comma-separated list of tags.', verbose_name='tags')),
            ],
            options={
                'ordering': ('-enabled', 'normalized_name'),
                'db_table': 'vm_node',
                'permissions': (('view_statistics', 'Can view Node box and statistics.'),),
            },
            bases=(common.operations.OperatedMixin, models.Model),
        ),
        migrations.CreateModel(
            name='NodeActivity',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('activity_code', models.CharField(max_length=100, verbose_name='activity code')),
                ('readable_name_data', jsonfield.fields.JSONField(help_text='Human readable name of activity.', null=True, verbose_name='human readable name', blank=True)),
                ('task_uuid', models.CharField(null=True, max_length=50, blank=True, help_text='Celery task unique identifier.', unique=True, verbose_name='task_uuid')),
                ('started', models.DateTimeField(help_text='Time of activity initiation.', null=True, verbose_name='started at', blank=True)),
                ('finished', models.DateTimeField(help_text='Time of activity finalization.', null=True, verbose_name='finished at', blank=True)),
                ('succeeded', models.NullBooleanField(help_text='True, if the activity has finished successfully.')),
                ('result_data', jsonfield.fields.JSONField(help_text='Human readable result of activity.', null=True, verbose_name='result', blank=True)),
                ('node', models.ForeignKey(related_name='activity_log', verbose_name='node', to='vm.Node', help_text='Node this activity works on.')),
                ('parent', models.ForeignKey(related_name='children', blank=True, to='vm.NodeActivity', null=True)),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, help_text='The person who started this activity.', null=True, verbose_name='user')),
            ],
            options={
                'db_table': 'vm_nodeactivity',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Trait',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50, verbose_name='name')),
            ],
            options={
                'db_table': 'vm_trait',
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='node',
            name='traits',
            field=models.ManyToManyField(help_text='Declared traits.', to='vm.Trait', verbose_name='traits', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='instancetemplate',
            name='lease',
            field=models.ForeignKey(verbose_name='Lease', to='vm.Lease', help_text='Preferred expiration periods.'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='instancetemplate',
            name='owner',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='instancetemplate',
            name='parent',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='vm.InstanceTemplate', help_text='Template which this one is derived of.', null=True, verbose_name='parent template'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='instancetemplate',
            name='req_traits',
            field=models.ManyToManyField(help_text='A set of traits required for a node to declare to be suitable for hosting the VM.', to='vm.Trait', verbose_name='required traits', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='instancetemplate',
            name='tags',
            field=taggit.managers.TaggableManager(to='taggit.Tag', through='taggit.TaggedItem', blank=True, help_text='A comma-separated list of tags.', verbose_name='tags'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='instance',
            name='lease',
            field=models.ForeignKey(verbose_name='Lease', to='vm.Lease', help_text='Preferred expiration periods.'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='instance',
            name='node',
            field=models.ForeignKey(related_name='instance_set', blank=True, to='vm.Node', help_text='Current hypervisor of this instance.', null=True, verbose_name='host node'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='instance',
            name='owner',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='instance',
            name='req_traits',
            field=models.ManyToManyField(help_text='A set of traits required for a node to declare to be suitable for hosting the VM.', to='vm.Trait', verbose_name='required traits', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='instance',
            name='tags',
            field=taggit.managers.TaggableManager(to='taggit.Tag', through='taggit.TaggedItem', blank=True, help_text='A comma-separated list of tags.', verbose_name='tags'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='instance',
            name='template',
            field=models.ForeignKey(related_name='instance_set', on_delete=django.db.models.deletion.SET_NULL, blank=True, to='vm.InstanceTemplate', help_text='Template the instance derives from.', null=True, verbose_name='template'),
            preserve_default=True,
        ),
    ]
