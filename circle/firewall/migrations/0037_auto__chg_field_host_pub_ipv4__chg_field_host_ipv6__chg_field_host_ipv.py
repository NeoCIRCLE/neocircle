# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Host.pub_ipv4'
        db.alter_column(u'firewall_host', 'pub_ipv4', self.gf('firewall.fields.IPAddressField')(max_length=100, null=True))

        # Changing field 'Host.ipv6'
        db.alter_column(u'firewall_host', 'ipv6', self.gf('firewall.fields.IPAddressField')(max_length=100, unique=True, null=True))

        # Changing field 'Host.ipv4'
        db.alter_column(u'firewall_host', 'ipv4', self.gf('firewall.fields.IPAddressField')(unique=True, max_length=100))

        # Changing field 'Vlan.network4'
        db.alter_column(u'firewall_vlan', 'network4', self.gf('firewall.fields.IPNetworkField')(default='192.168.0.1/24', max_length=100))

        # Changing field 'Record.address'
        db.alter_column(u'firewall_record', 'address', self.gf('django.db.models.fields.CharField')(default='127.0.0.1', max_length=40))

    def backwards(self, orm):

        # Changing field 'Host.pub_ipv4'
        db.alter_column(u'firewall_host', 'pub_ipv4', self.gf('django.db.models.fields.GenericIPAddressField')(max_length=39, null=True))

        # Changing field 'Host.ipv6'
        db.alter_column(u'firewall_host', 'ipv6', self.gf('django.db.models.fields.GenericIPAddressField')(unique=True, max_length=39, null=True))

        # Changing field 'Host.ipv4'
        db.alter_column(u'firewall_host', 'ipv4', self.gf('django.db.models.fields.GenericIPAddressField')(max_length=39, unique=True))

        # Changing field 'Vlan.network4'
        db.alter_column(u'firewall_vlan', 'network4', self.gf('firewall.fields.IPNetworkField')(max_length=100, null=True))

        # Changing field 'Record.address'
        db.alter_column(u'firewall_record', 'address', self.gf('django.db.models.fields.CharField')(max_length=40, null=True))

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
        u'firewall.blacklist': {
            'Meta': {'object_name': 'Blacklist'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['firewall.Host']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ipv4': ('django.db.models.fields.GenericIPAddressField', [], {'unique': 'True', 'max_length': '39'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'reason': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'snort_message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'default': "'tempban'", 'max_length': '10'})
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
        u'firewall.ethernetdevice': {
            'Meta': {'object_name': 'EthernetDevice'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'switch_port': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'ethernet_devices'", 'to': u"orm['firewall.SwitchPort']"})
        },
        u'firewall.firewall': {
            'Meta': {'object_name': 'Firewall'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'})
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
        u'firewall.record': {
            'Meta': {'ordering': "('domain', 'name')", 'object_name': 'Record'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'domain': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['firewall.Domain']"}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['firewall.Host']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'ttl': ('django.db.models.fields.IntegerField', [], {'default': '600'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '6'})
        },
        u'firewall.rule': {
            'Meta': {'ordering': "('direction', 'proto', 'sport', 'dport', 'nat_dport', 'host')", 'object_name': 'Rule'},
            'accept': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'direction': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'dport': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'extra': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'firewall': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'rules'", 'null': 'True', 'to': u"orm['firewall.Firewall']"}),
            'foreign_network': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'ForeignRules'", 'to': u"orm['firewall.VlanGroup']"}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'rules'", 'null': 'True', 'to': u"orm['firewall.Host']"}),
            'hostgroup': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'rules'", 'null': 'True', 'to': u"orm['firewall.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'nat': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'nat_dport': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'proto': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'sport': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'vlan': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'rules'", 'null': 'True', 'to': u"orm['firewall.Vlan']"}),
            'vlangroup': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'rules'", 'null': 'True', 'to': u"orm['firewall.VlanGroup']"})
        },
        u'firewall.switchport': {
            'Meta': {'object_name': 'SwitchPort'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'tagged_vlans': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'tagged_ports'", 'null': 'True', 'to': u"orm['firewall.VlanGroup']"}),
            'untagged_vlan': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'untagged_ports'", 'to': u"orm['firewall.Vlan']"})
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
            'network4': ('firewall.fields.IPNetworkField', [], {'max_length': '100'}),
            'network6': ('firewall.fields.IPNetworkField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'reverse_domain': ('django.db.models.fields.TextField', [], {'default': "'%(d)d.%(c)d.%(b)d.%(a)d.in-addr.arpa'"}),
            'snat_ip': ('django.db.models.fields.GenericIPAddressField', [], {'max_length': '39', 'null': 'True', 'blank': 'True'}),
            'snat_to': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['firewall.Vlan']", 'null': 'True', 'blank': 'True'}),
            'vid': ('django.db.models.fields.IntegerField', [], {'unique': 'True'})
        },
        u'firewall.vlangroup': {
            'Meta': {'object_name': 'VlanGroup'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'vlans': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['firewall.Vlan']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['firewall']