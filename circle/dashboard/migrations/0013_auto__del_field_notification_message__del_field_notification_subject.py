# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Notification.message'
        db.delete_column(u'dashboard_notification', 'message')

        # Deleting field 'Notification.subject'
        db.delete_column(u'dashboard_notification', 'subject')


    def backwards(self, orm):
        # Adding field 'Notification.message'
        db.add_column(u'dashboard_notification', 'message',
                      self.gf('django.db.models.fields.TextField')(default=''),
                      keep_default=False)

        # Adding field 'Notification.subject'
        db.add_column(u'dashboard_notification', 'subject',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=128),
                      keep_default=False)


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
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'dashboard.favourite': {
            'Meta': {'object_name': 'Favourite'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instance': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['vm.Instance']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'dashboard.futuremember': {
            'Meta': {'unique_together': "(('org_id', 'group'),)", 'object_name': 'FutureMember'},
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'org_id': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        u'dashboard.groupprofile': {
            'Meta': {'object_name': 'GroupProfile'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'group': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.Group']", 'unique': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'org_id': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True', 'blank': 'True'})
        },
        u'dashboard.notification': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Notification'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message_data': ('jsonfield.fields.JSONField', [], {'null': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'status': ('model_utils.fields.StatusField', [], {'default': "'new'", 'max_length': '100', u'no_check_for_status': 'True'}),
            'subject_data': ('jsonfield.fields.JSONField', [], {'null': 'True'}),
            'to': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'valid_until': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'})
        },
        u'dashboard.profile': {
            'Meta': {'object_name': 'Profile'},
            'email_notifications': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instance_limit': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'org_id': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'preferred_language': ('django.db.models.fields.CharField', [], {'default': "'en'", 'max_length': '32'}),
            'use_gravatar': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True'})
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
            'Meta': {'ordering': "('normalized_hostname', 'vlan')", 'unique_together': "(('hostname', 'vlan'),)", 'object_name': 'Host'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'external_ipv4': ('firewall.fields.IPAddressField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['firewall.Group']", 'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ipv4': ('firewall.fields.IPAddressField', [], {'unique': 'True', 'max_length': '100'}),
            'ipv6': ('firewall.fields.IPAddressField', [], {'max_length': '100', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'mac': ('firewall.fields.MACAddressField', [], {'unique': 'True', 'max_length': '17'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'normalized_hostname': ('common.models.HumanSortField', [], {'default': "''", 'maximum_number_length': '4', 'max_length': '80', 'monitor': "'hostname'", 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
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
            'host_ipv6_prefixlen': ('django.db.models.fields.IntegerField', [], {'default': '112'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ipv6_template': ('django.db.models.fields.TextField', [], {'default': "'2001:738:2001:4031:%(b)d:%(c)d:%(d)d:0'"}),
            'managed': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'network4': ('firewall.fields.IPNetworkField', [], {'max_length': '100'}),
            'network6': ('firewall.fields.IPNetworkField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'network_type': ('django.db.models.fields.CharField', [], {'default': "'portforward'", 'max_length': '20'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'reverse_domain': ('django.db.models.fields.TextField', [], {'default': "'%(d)d.%(c)d.%(b)d.%(a)d.in-addr.arpa'"}),
            'snat_ip': ('django.db.models.fields.GenericIPAddressField', [], {'max_length': '39', 'null': 'True', 'blank': 'True'}),
            'snat_to': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['firewall.Vlan']", 'null': 'True', 'blank': 'True'}),
            'vid': ('django.db.models.fields.IntegerField', [], {'unique': 'True'})
        },
        u'storage.datastore': {
            'Meta': {'ordering': "[u'name']", 'object_name': 'DataStore'},
            'hostname': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'path': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'})
        },
        u'storage.disk': {
            'Meta': {'ordering': "[u'name']", 'object_name': 'Disk'},
            'base': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'derivatives'", 'null': 'True', 'to': u"orm['storage.Disk']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'datastore': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['storage.DataStore']"}),
            'destroyed': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'dev_num': ('django.db.models.fields.CharField', [], {'default': "u'a'", 'max_length': '1'}),
            'filename': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '256'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_ready': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'size': ('sizefield.models.FileSizeField', [], {'default': 'None', 'null': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '10'})
        },
        u'vm.instance': {
            'Meta': {'ordering': "(u'pk',)", 'object_name': 'Instance'},
            'access_method': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'active_since': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'arch': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'boot_menu': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'destroyed_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'disks': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "u'instance_set'", 'symmetrical': 'False', 'to': u"orm['storage.Disk']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_base': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
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
            'status': ('model_utils.fields.StatusField', [], {'default': "u'NOSTATE'", 'max_length': '100', u'no_check_for_status': 'True'}),
            'status_changed': ('model_utils.fields.MonitorField', [], {'default': 'datetime.datetime.now', u'monitor': "u'status'"}),
            'system': ('django.db.models.fields.TextField', [], {}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'instance_set'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': u"orm['vm.InstanceTemplate']"}),
            'time_of_delete': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'time_of_suspend': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'vnc_port': ('django.db.models.fields.IntegerField', [], {'default': 'None', 'unique': 'True', 'null': 'True', 'blank': 'True'})
        },
        u'vm.instancetemplate': {
            'Meta': {'ordering': "(u'name',)", 'object_name': 'InstanceTemplate'},
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
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'num_cores': ('django.db.models.fields.IntegerField', [], {}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['vm.InstanceTemplate']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'priority': ('django.db.models.fields.IntegerField', [], {}),
            'ram_size': ('django.db.models.fields.IntegerField', [], {}),
            'raw_data': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'req_traits': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['vm.Trait']", 'symmetrical': 'False', 'blank': 'True'}),
            'system': ('django.db.models.fields.TextField', [], {})
        },
        u'vm.lease': {
            'Meta': {'ordering': "[u'name']", 'object_name': 'Lease'},
            'delete_interval_seconds': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'suspend_interval_seconds': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'vm.node': {
            'Meta': {'ordering': "(u'-enabled', u'normalized_name')", 'object_name': 'Node'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['firewall.Host']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'normalized_name': ('common.models.HumanSortField', [], {'default': "''", 'maximum_number_length': '4', 'max_length': '100', 'monitor': "u'name'", 'blank': 'True'}),
            'overcommit': ('django.db.models.fields.FloatField', [], {'default': '1.0'}),
            'priority': ('django.db.models.fields.IntegerField', [], {}),
            'traits': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['vm.Trait']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'vm.trait': {
            'Meta': {'object_name': 'Trait'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['dashboard']