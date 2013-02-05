# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Record.address'
        db.alter_column('firewall_record', 'address', self.gf('django.db.models.fields.CharField')(max_length=40, null=True))

    def backwards(self, orm):

        # User chose to not deal with backwards NULL issues for 'Record.address'
        raise RuntimeError("Cannot reverse this migration. 'Record.address' and its values cannot be restored.")

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'firewall.alias': {
            'Meta': {'object_name': 'Alias'},
            'alias': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['firewall.Host']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'firewall.domain': {
            'Meta': {'object_name': 'Domain'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'ttl': ('django.db.models.fields.IntegerField', [], {'default': '600'})
        },
        'firewall.firewall': {
            'Meta': {'object_name': 'Firewall'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'})
        },
        'firewall.group': {
            'Meta': {'object_name': 'Group'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'firewall.host': {
            'Meta': {'object_name': 'Host'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['firewall.Group']", 'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ipv4': ('django.db.models.fields.GenericIPAddressField', [], {'unique': 'True', 'max_length': '39'}),
            'ipv6': ('django.db.models.fields.GenericIPAddressField', [], {'max_length': '39', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'mac': ('firewall.fields.MACAddressField', [], {'unique': 'True', 'max_length': '17'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'pub_ipv4': ('django.db.models.fields.GenericIPAddressField', [], {'max_length': '39', 'null': 'True', 'blank': 'True'}),
            'reverse': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'shared_ip': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'vlan': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['firewall.Vlan']"})
        },
        'firewall.record': {
            'Meta': {'object_name': 'Record'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'domain': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['firewall.Domain']"}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['firewall.Host']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'ttl': ('django.db.models.fields.IntegerField', [], {'default': '600'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '6'})
        },
        'firewall.rule': {
            'Meta': {'object_name': 'Rule'},
            'accept': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'direction': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'dport': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'extra': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'firewall': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'rules'", 'null': 'True', 'to': "orm['firewall.Firewall']"}),
            'foreign_network': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'ForeignRules'", 'to': "orm['firewall.VlanGroup']"}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'rules'", 'null': 'True', 'to': "orm['firewall.Host']"}),
            'hostgroup': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'rules'", 'null': 'True', 'to': "orm['firewall.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'nat': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'nat_dport': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'proto': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'r_type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'sport': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'vlan': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'rules'", 'null': 'True', 'to': "orm['firewall.Vlan']"}),
            'vlangroup': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'rules'", 'null': 'True', 'to': "orm['firewall.VlanGroup']"})
        },
        'firewall.setting': {
            'Meta': {'object_name': 'Setting'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'firewall.vlan': {
            'Meta': {'object_name': 'Vlan'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'dhcp_pool': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'domain': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'interface': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'ipv4': ('django.db.models.fields.GenericIPAddressField', [], {'unique': 'True', 'max_length': '39'}),
            'ipv6': ('django.db.models.fields.GenericIPAddressField', [], {'unique': 'True', 'max_length': '39'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'net4': ('django.db.models.fields.GenericIPAddressField', [], {'unique': 'True', 'max_length': '39'}),
            'net6': ('django.db.models.fields.GenericIPAddressField', [], {'unique': 'True', 'max_length': '39'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'prefix4': ('django.db.models.fields.IntegerField', [], {'default': '16'}),
            'prefix6': ('django.db.models.fields.IntegerField', [], {'default': '80'}),
            'snat_ip': ('django.db.models.fields.GenericIPAddressField', [], {'max_length': '39', 'null': 'True', 'blank': 'True'}),
            'snat_to': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['firewall.Vlan']", 'null': 'True', 'blank': 'True'}),
            'vid': ('django.db.models.fields.IntegerField', [], {'unique': 'True'})
        },
        'firewall.vlangroup': {
            'Meta': {'object_name': 'VlanGroup'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'vlans': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['firewall.Vlan']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['firewall']