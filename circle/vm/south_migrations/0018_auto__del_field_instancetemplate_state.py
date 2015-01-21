# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'InstanceTemplate.state'
        db.delete_column(u'vm_instancetemplate', 'state')


    def backwards(self, orm):
        # Adding field 'InstanceTemplate.state'
        db.add_column(u'vm_instancetemplate', 'state',
                      self.gf('django.db.models.fields.CharField')(default=u'NEW', max_length=10),
                      keep_default=False)


    models = {
        u'acl.level': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Level'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'weight': ('django.db.models.fields.IntegerField', [], {'null': 'True'})
        },
        u'acl.objectlevel': {
            'Meta': {'unique_together': "(('content_type', 'object_id', 'level'),)", 'object_name': 'ObjectLevel'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['acl.Level']"}),
            'object_id': ('django.db.models.fields.IntegerField', [], {}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.User']", 'symmetrical': 'False'})
        },
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
            'Meta': {'unique_together': "(('hostname', 'vlan'),)", 'object_name': 'Host'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['firewall.Group']", 'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ipv4': ('firewall.fields.IPAddressField', [], {'unique': 'True', 'max_length': '100'}),
            'ipv6': ('firewall.fields.IPAddressField', [], {'max_length': '100', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'mac': ('firewall.fields.MACAddressField', [], {'unique': 'True', 'max_length': '17'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'pub_ipv4': ('firewall.fields.IPAddressField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
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
            'ipv6_template': ('django.db.models.fields.TextField', [], {'default': "'2001:738:2001:4031:%(b)d:%(c)d:%(d)d:0'"}),
            'managed': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'network4': ('firewall.fields.IPNetworkField', [], {'max_length': '100'}),
            'network6': ('firewall.fields.IPNetworkField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'network_type': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'reverse_domain': ('django.db.models.fields.TextField', [], {'default': "'%(d)d.%(c)d.%(b)d.%(a)d.in-addr.arpa'"}),
            'snat_ip': ('django.db.models.fields.GenericIPAddressField', [], {'max_length': '39', 'null': 'True', 'blank': 'True'}),
            'snat_to': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['firewall.Vlan']", 'null': 'True', 'blank': 'True'}),
            'vid': ('django.db.models.fields.IntegerField', [], {'unique': 'True'})
        },
        u'storage.datastore': {
            'Meta': {'ordering': "['name']", 'object_name': 'DataStore'},
            'hostname': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'path': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'})
        },
        u'storage.disk': {
            'Meta': {'ordering': "['name']", 'object_name': 'Disk'},
            'base': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'derivatives'", 'null': 'True', 'to': u"orm['storage.Disk']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'datastore': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['storage.DataStore']"}),
            'destroyed': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'dev_num': ('django.db.models.fields.CharField', [], {'default': "'a'", 'max_length': '1'}),
            'filename': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'ready': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'size': ('sizefield.models.FileSizeField', [], {}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '10'})
        },
        u'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        u'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'taggit_taggeditem_tagged_items'", 'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'taggit_taggeditem_items'", 'to': u"orm['taggit.Tag']"})
        },
        u'vm.instance': {
            'Meta': {'ordering': "[u'pk']", 'object_name': 'Instance'},
            'access_method': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'active_since': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'arch': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'boot_menu': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'destroyed': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'disks': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "u'instance_set'", 'symmetrical': 'False', 'to': u"orm['storage.Disk']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lease': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['vm.Lease']"}),
            'max_ram_size': ('django.db.models.fields.IntegerField', [], {}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'node': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'instance_set'", 'null': 'True', 'to': u"orm['vm.Node']"}),
            'num_cores': ('django.db.models.fields.IntegerField', [], {}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'priority': ('django.db.models.fields.IntegerField', [], {}),
            'pw': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'ram_size': ('django.db.models.fields.IntegerField', [], {}),
            'raw_data': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'req_traits': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['vm.Trait']", 'symmetrical': 'False', 'blank': 'True'}),
            'system': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'instance_set'", 'null': 'True', 'to': u"orm['vm.InstanceTemplate']"}),
            'time_of_delete': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'time_of_suspend': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'vnc_port': ('django.db.models.fields.IntegerField', [], {'default': 'None', 'unique': 'True', 'null': 'True', 'blank': 'True'})
        },
        u'vm.instanceactivity': {
            'Meta': {'ordering': "[u'-finished', u'-started', u'instance', u'-id']", 'object_name': 'InstanceActivity'},
            'activity_code': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instance': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'activity_log'", 'to': u"orm['vm.Instance']"}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': u"orm['vm.InstanceActivity']"}),
            'result': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'resultant_state': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'started': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'succeeded': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'task_uuid': ('django.db.models.fields.CharField', [], {'max_length': '50', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        u'vm.instancetemplate': {
            'Meta': {'ordering': "[u'name']", 'object_name': 'InstanceTemplate'},
            'access_method': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'arch': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'boot_menu': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'disks': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "u'template_set'", 'symmetrical': 'False', 'to': u"orm['storage.Disk']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lease': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['vm.Lease']"}),
            'max_ram_size': ('django.db.models.fields.IntegerField', [], {}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'num_cores': ('django.db.models.fields.IntegerField', [], {}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['vm.InstanceTemplate']", 'null': 'True', 'blank': 'True'}),
            'priority': ('django.db.models.fields.IntegerField', [], {}),
            'ram_size': ('django.db.models.fields.IntegerField', [], {}),
            'raw_data': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'req_traits': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['vm.Trait']", 'symmetrical': 'False', 'blank': 'True'}),
            'system': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'vm.interface': {
            'Meta': {'object_name': 'Interface'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['firewall.Host']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instance': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'interface_set'", 'to': u"orm['vm.Instance']"}),
            'vlan': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'vm_interface'", 'to': u"orm['firewall.Vlan']"})
        },
        u'vm.interfacetemplate': {
            'Meta': {'object_name': 'InterfaceTemplate'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'managed': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'interface_set'", 'to': u"orm['vm.InstanceTemplate']"}),
            'vlan': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['firewall.Vlan']"})
        },
        u'vm.lease': {
            'Meta': {'ordering': "[u'name']", 'object_name': 'Lease'},
            'delete_interval_seconds': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'suspend_interval_seconds': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'vm.namedbaseresourceconfig': {
            'Meta': {'object_name': 'NamedBaseResourceConfig'},
            'arch': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_ram_size': ('django.db.models.fields.IntegerField', [], {}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'num_cores': ('django.db.models.fields.IntegerField', [], {}),
            'priority': ('django.db.models.fields.IntegerField', [], {}),
            'ram_size': ('django.db.models.fields.IntegerField', [], {})
        },
        u'vm.node': {
            'Meta': {'object_name': 'Node'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['firewall.Host']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'overcommit': ('django.db.models.fields.FloatField', [], {'default': '1.0'}),
            'priority': ('django.db.models.fields.IntegerField', [], {}),
            'traits': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['vm.Trait']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'vm.nodeactivity': {
            'Meta': {'object_name': 'NodeActivity'},
            'activity_code': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'node': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'activity_log'", 'to': u"orm['vm.Node']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': u"orm['vm.NodeActivity']"}),
            'result': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'started': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'succeeded': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'task_uuid': ('django.db.models.fields.CharField', [], {'max_length': '50', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        u'vm.trait': {
            'Meta': {'object_name': 'Trait'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['vm']