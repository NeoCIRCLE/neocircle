# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'NamedBaseResourceConfig'
        db.create_table(u'vm_namedbaseresourceconfig', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('num_cores', self.gf('django.db.models.fields.IntegerField')()),
            ('ram_size', self.gf('django.db.models.fields.IntegerField')()),
            ('max_ram_size', self.gf('django.db.models.fields.IntegerField')()),
            ('arch', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('priority', self.gf('django.db.models.fields.IntegerField')()),
            ('boot_menu', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('raw_data', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
        ))
        db.send_create_signal(u'vm', ['NamedBaseResourceConfig'])

        # Adding model 'Node'
        db.create_table(u'vm_node', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
            ('num_cores', self.gf('django.db.models.fields.IntegerField')()),
            ('ram_size', self.gf('django.db.models.fields.IntegerField')()),
            ('priority', self.gf('django.db.models.fields.IntegerField')()),
            ('host', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['firewall.Host'])),
            ('enabled', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'vm', ['Node'])

        # Adding model 'NodeActivity'
        db.create_table(u'vm_nodeactivity', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('activity_code', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('task_uuid', self.gf('django.db.models.fields.CharField')(max_length=50, unique=True, null=True, blank=True)),
            ('node', self.gf('django.db.models.fields.related.ForeignKey')(related_name='activity_log', to=orm['vm.Node'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('started', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('finished', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('result', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('status', self.gf('django.db.models.fields.CharField')(default='PENDING', max_length=50)),
        ))
        db.send_create_signal(u'vm', ['NodeActivity'])

        # Adding model 'Lease'
        db.create_table(u'vm_lease', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('suspend_interval_seconds', self.gf('django.db.models.fields.IntegerField')()),
            ('delete_interval_seconds', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal(u'vm', ['Lease'])

        # Adding model 'InstanceTemplate'
        db.create_table(u'vm_instancetemplate', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('num_cores', self.gf('django.db.models.fields.IntegerField')()),
            ('ram_size', self.gf('django.db.models.fields.IntegerField')()),
            ('max_ram_size', self.gf('django.db.models.fields.IntegerField')()),
            ('arch', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('priority', self.gf('django.db.models.fields.IntegerField')()),
            ('boot_menu', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('raw_data', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['vm.InstanceTemplate'], null=True, blank=True)),
            ('system', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('access_method', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('state', self.gf('django.db.models.fields.CharField')(default='NEW', max_length=10)),
            ('lease', self.gf('django.db.models.fields.related.ForeignKey')(related_name='template_set', to=orm['vm.Lease'])),
        ))
        db.send_create_signal(u'vm', ['InstanceTemplate'])

        # Adding M2M table for field disks on 'InstanceTemplate'
        m2m_table_name = db.shorten_name(u'vm_instancetemplate_disks')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('instancetemplate', models.ForeignKey(orm[u'vm.instancetemplate'], null=False)),
            ('disk', models.ForeignKey(orm[u'storage.disk'], null=False))
        ))
        db.create_unique(m2m_table_name, ['instancetemplate_id', 'disk_id'])

        # Adding model 'InterfaceTemplate'
        db.create_table(u'vm_interfacetemplate', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('vlan', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['firewall.Vlan'])),
            ('managed', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('template', self.gf('django.db.models.fields.related.ForeignKey')(related_name='interface_set', to=orm['vm.InstanceTemplate'])),
        ))
        db.send_create_signal(u'vm', ['InterfaceTemplate'])

        # Adding model 'Instance'
        db.create_table(u'vm_instance', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('num_cores', self.gf('django.db.models.fields.IntegerField')()),
            ('ram_size', self.gf('django.db.models.fields.IntegerField')()),
            ('max_ram_size', self.gf('django.db.models.fields.IntegerField')()),
            ('arch', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('priority', self.gf('django.db.models.fields.IntegerField')()),
            ('boot_menu', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('raw_data', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('template', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='instance_set', null=True, to=orm['vm.InstanceTemplate'])),
            ('pw', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('time_of_suspend', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True, blank=True)),
            ('time_of_delete', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True, blank=True)),
            ('active_since', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('node', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='instance_set', null=True, to=orm['vm.Node'])),
            ('state', self.gf('django.db.models.fields.CharField')(default='NOSTATE', max_length=20)),
            ('lease', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['vm.Lease'])),
            ('access_method', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
        ))
        db.send_create_signal(u'vm', ['Instance'])

        # Adding M2M table for field disks on 'Instance'
        m2m_table_name = db.shorten_name(u'vm_instance_disks')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('instance', models.ForeignKey(orm[u'vm.instance'], null=False)),
            ('disk', models.ForeignKey(orm[u'storage.disk'], null=False))
        ))
        db.create_unique(m2m_table_name, ['instance_id', 'disk_id'])

        # Adding model 'InstanceActivity'
        db.create_table(u'vm_instanceactivity', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('activity_code', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('task_uuid', self.gf('django.db.models.fields.CharField')(max_length=50, unique=True, null=True, blank=True)),
            ('instance', self.gf('django.db.models.fields.related.ForeignKey')(related_name='activity_log', to=orm['vm.Instance'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('started', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('finished', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('result', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('state', self.gf('django.db.models.fields.CharField')(default='PENDING', max_length=50)),
        ))
        db.send_create_signal(u'vm', ['InstanceActivity'])

        # Adding model 'Interface'
        db.create_table(u'vm_interface', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('vlan', self.gf('django.db.models.fields.related.ForeignKey')(related_name='vm_interface', to=orm['firewall.Vlan'])),
            ('host', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['firewall.Host'], null=True, blank=True)),
            ('instance', self.gf('django.db.models.fields.related.ForeignKey')(related_name='interface_set', to=orm['vm.Instance'])),
        ))
        db.send_create_signal(u'vm', ['Interface'])


    def backwards(self, orm):
        # Deleting model 'NamedBaseResourceConfig'
        db.delete_table(u'vm_namedbaseresourceconfig')

        # Deleting model 'Node'
        db.delete_table(u'vm_node')

        # Deleting model 'NodeActivity'
        db.delete_table(u'vm_nodeactivity')

        # Deleting model 'Lease'
        db.delete_table(u'vm_lease')

        # Deleting model 'InstanceTemplate'
        db.delete_table(u'vm_instancetemplate')

        # Removing M2M table for field disks on 'InstanceTemplate'
        db.delete_table(db.shorten_name(u'vm_instancetemplate_disks'))

        # Deleting model 'InterfaceTemplate'
        db.delete_table(u'vm_interfacetemplate')

        # Deleting model 'Instance'
        db.delete_table(u'vm_instance')

        # Removing M2M table for field disks on 'Instance'
        db.delete_table(db.shorten_name(u'vm_instance_disks'))

        # Deleting model 'InstanceActivity'
        db.delete_table(u'vm_instanceactivity')

        # Deleting model 'Interface'
        db.delete_table(u'vm_interface')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'firewall.domain': {
            'Meta': {'object_name': 'Domain'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'ttl': ('django.db.models.fields.IntegerField', [], {'default': '600'})
        },
        u'firewall.group': {
            'Meta': {'object_name': 'Group'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        u'firewall.host': {
            'Meta': {'object_name': 'Host'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['firewall.Group']", 'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ipv4': ('django.db.models.fields.GenericIPAddressField', [], {'unique': 'True', 'max_length': '39'}),
            'ipv6': ('django.db.models.fields.GenericIPAddressField', [], {'max_length': '39', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'mac': ('firewall.fields.MACAddressField', [], {'unique': 'True', 'max_length': '17'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'pub_ipv4': ('django.db.models.fields.GenericIPAddressField', [], {'max_length': '39', 'null': 'True', 'blank': 'True'}),
            'reverse': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'shared_ip': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'vlan': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['firewall.Vlan']"})
        },
        u'firewall.vlan': {
            'Meta': {'object_name': 'Vlan'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'dhcp_pool': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'domain': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['firewall.Domain']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'interface': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'network4': ('firewall.fields.IPNetworkField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'network6': ('firewall.fields.IPNetworkField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'reverse_domain': ('django.db.models.fields.TextField', [], {'default': "'%(d)d.%(c)d.%(b)d.%(a)d.in-addr.arpa'"}),
            'snat_ip': ('django.db.models.fields.GenericIPAddressField', [], {'max_length': '39', 'null': 'True', 'blank': 'True'}),
            'snat_to': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['firewall.Vlan']", 'null': 'True', 'blank': 'True'}),
            'vid': ('django.db.models.fields.IntegerField', [], {'unique': 'True'})
        },
        u'storage.datastore': {
            'Meta': {'ordering': "['name']", 'object_name': 'DataStore'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'path': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'})
        },
        u'storage.disk': {
            'Meta': {'ordering': "['name']", 'object_name': 'Disk'},
            'base': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'derivatives'", 'null': 'True', 'to': u"orm['storage.Disk']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'datastore': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['storage.DataStore']"}),
            'dev_num': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'format': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'ready': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'size': ('django.db.models.fields.IntegerField', [], {}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '10'})
        },
        u'vm.instance': {
            'Meta': {'ordering': "['pk']", 'object_name': 'Instance'},
            'access_method': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'active_since': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'arch': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'boot_menu': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'disks': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'instance_set'", 'symmetrical': 'False', 'to': u"orm['storage.Disk']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lease': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['vm.Lease']"}),
            'max_ram_size': ('django.db.models.fields.IntegerField', [], {}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'node': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'instance_set'", 'null': 'True', 'to': u"orm['vm.Node']"}),
            'num_cores': ('django.db.models.fields.IntegerField', [], {}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'priority': ('django.db.models.fields.IntegerField', [], {}),
            'pw': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'ram_size': ('django.db.models.fields.IntegerField', [], {}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'NOSTATE'", 'max_length': '20'}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'instance_set'", 'null': 'True', 'to': u"orm['vm.InstanceTemplate']"}),
            'time_of_delete': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'time_of_suspend': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'})
        },
        u'vm.instanceactivity': {
            'Meta': {'object_name': 'InstanceActivity'},
            'activity_code': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instance': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'activity_log'", 'to': u"orm['vm.Instance']"}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'result': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'started': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'PENDING'", 'max_length': '50'}),
            'task_uuid': ('django.db.models.fields.CharField', [], {'max_length': '50', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        u'vm.instancetemplate': {
            'Meta': {'ordering': "['name']", 'object_name': 'InstanceTemplate'},
            'access_method': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'arch': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'boot_menu': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'disks': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'template_set'", 'symmetrical': 'False', 'to': u"orm['storage.Disk']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lease': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'template_set'", 'to': u"orm['vm.Lease']"}),
            'max_ram_size': ('django.db.models.fields.IntegerField', [], {}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'num_cores': ('django.db.models.fields.IntegerField', [], {}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['vm.InstanceTemplate']", 'null': 'True', 'blank': 'True'}),
            'priority': ('django.db.models.fields.IntegerField', [], {}),
            'ram_size': ('django.db.models.fields.IntegerField', [], {}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'NEW'", 'max_length': '10'}),
            'system': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'vm.interface': {
            'Meta': {'object_name': 'Interface'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['firewall.Host']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instance': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'interface_set'", 'to': u"orm['vm.Instance']"}),
            'vlan': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'vm_interface'", 'to': u"orm['firewall.Vlan']"})
        },
        u'vm.interfacetemplate': {
            'Meta': {'object_name': 'InterfaceTemplate'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'managed': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'interface_set'", 'to': u"orm['vm.InstanceTemplate']"}),
            'vlan': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['firewall.Vlan']"})
        },
        u'vm.lease': {
            'Meta': {'ordering': "['name']", 'object_name': 'Lease'},
            'delete_interval_seconds': ('django.db.models.fields.IntegerField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'suspend_interval_seconds': ('django.db.models.fields.IntegerField', [], {})
        },
        u'vm.namedbaseresourceconfig': {
            'Meta': {'object_name': 'NamedBaseResourceConfig'},
            'arch': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'boot_menu': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_ram_size': ('django.db.models.fields.IntegerField', [], {}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'num_cores': ('django.db.models.fields.IntegerField', [], {}),
            'priority': ('django.db.models.fields.IntegerField', [], {}),
            'ram_size': ('django.db.models.fields.IntegerField', [], {}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        u'vm.node': {
            'Meta': {'object_name': 'Node'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['firewall.Host']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'num_cores': ('django.db.models.fields.IntegerField', [], {}),
            'priority': ('django.db.models.fields.IntegerField', [], {}),
            'ram_size': ('django.db.models.fields.IntegerField', [], {})
        },
        u'vm.nodeactivity': {
            'Meta': {'object_name': 'NodeActivity'},
            'activity_code': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'node': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'activity_log'", 'to': u"orm['vm.Node']"}),
            'result': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'started': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'PENDING'", 'max_length': '50'}),
            'task_uuid': ('django.db.models.fields.CharField', [], {'max_length': '50', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['vm']