# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'VlanGroup'
        db.create_table('firewall_vlangroup', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=20)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('firewall', ['VlanGroup'])

        # Adding M2M table for field vlans on 'VlanGroup'
        db.create_table('firewall_vlangroup_vlans', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('vlangroup', models.ForeignKey(orm['firewall.vlangroup'], null=False)),
            ('vlan', models.ForeignKey(orm['firewall.vlan'], null=False))
        ))
        db.create_unique('firewall_vlangroup_vlans', ['vlangroup_id', 'vlan_id'])

        # Removing M2M table for field rules on 'Host'
        db.delete_table('firewall_host_rules')

        # Adding field 'Setting.description'
        db.add_column('firewall_setting', 'description',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)

        # Adding field 'Group.description'
        db.add_column('firewall_group', 'description',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)

        # Adding field 'Group.owner'
        db.add_column('firewall_group', 'owner',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True),
                      keep_default=False)

        # Removing M2M table for field rules on 'Group'
        db.delete_table('firewall_group_rules')

        # Adding field 'Vlan.owner'
        db.add_column('firewall_vlan', 'owner',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True),
                      keep_default=False)

        # Removing M2M table for field rules on 'Vlan'
        db.delete_table('firewall_vlan_rules')

        # Adding field 'Rule.foreign_network'
        db.add_column('firewall_rule', 'foreign_network',
                      self.gf('django.db.models.fields.related.ForeignKey')(default=1, related_name='ForeignRules', to=orm['firewall.VlanGroup']),
                      keep_default=False)

        # Adding field 'Rule.vlan'
        db.add_column('firewall_rule', 'vlan',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['firewall.Vlan'], null=True, blank=True),
                      keep_default=False)

        # Adding field 'Rule.vlangroup'
        db.add_column('firewall_rule', 'vlangroup',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['firewall.VlanGroup'], null=True, blank=True),
                      keep_default=False)

        # Adding field 'Rule.host'
        db.add_column('firewall_rule', 'host',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['firewall.Host'], null=True, blank=True),
                      keep_default=False)

        # Adding field 'Rule.hostgroup'
        db.add_column('firewall_rule', 'hostgroup',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['firewall.Group'], null=True, blank=True),
                      keep_default=False)

        # Removing M2M table for field vlan on 'Rule'
        db.delete_table('firewall_rule_vlan')


    def backwards(self, orm):
        # Deleting model 'VlanGroup'
        db.delete_table('firewall_vlangroup')

        # Removing M2M table for field vlans on 'VlanGroup'
        db.delete_table('firewall_vlangroup_vlans')

        # Adding M2M table for field rules on 'Host'
        db.create_table('firewall_host_rules', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('host', models.ForeignKey(orm['firewall.host'], null=False)),
            ('rule', models.ForeignKey(orm['firewall.rule'], null=False))
        ))
        db.create_unique('firewall_host_rules', ['host_id', 'rule_id'])

        # Deleting field 'Setting.description'
        db.delete_column('firewall_setting', 'description')

        # Deleting field 'Group.description'
        db.delete_column('firewall_group', 'description')

        # Deleting field 'Group.owner'
        db.delete_column('firewall_group', 'owner_id')

        # Adding M2M table for field rules on 'Group'
        db.create_table('firewall_group_rules', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('group', models.ForeignKey(orm['firewall.group'], null=False)),
            ('rule', models.ForeignKey(orm['firewall.rule'], null=False))
        ))
        db.create_unique('firewall_group_rules', ['group_id', 'rule_id'])

        # Deleting field 'Vlan.owner'
        db.delete_column('firewall_vlan', 'owner_id')

        # Adding M2M table for field rules on 'Vlan'
        db.create_table('firewall_vlan_rules', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('vlan', models.ForeignKey(orm['firewall.vlan'], null=False)),
            ('rule', models.ForeignKey(orm['firewall.rule'], null=False))
        ))
        db.create_unique('firewall_vlan_rules', ['vlan_id', 'rule_id'])

        # Deleting field 'Rule.foreign_network'
        db.delete_column('firewall_rule', 'foreign_network_id')

        # Deleting field 'Rule.vlan'
        db.delete_column('firewall_rule', 'vlan_id')

        # Deleting field 'Rule.vlangroup'
        db.delete_column('firewall_rule', 'vlangroup_id')

        # Deleting field 'Rule.host'
        db.delete_column('firewall_rule', 'host_id')

        # Deleting field 'Rule.hostgroup'
        db.delete_column('firewall_rule', 'hostgroup_id')

        # Adding M2M table for field vlan on 'Rule'
        db.create_table('firewall_rule_vlan', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('rule', models.ForeignKey(orm['firewall.rule'], null=False)),
            ('vlan', models.ForeignKey(orm['firewall.vlan'], null=False))
        ))
        db.create_unique('firewall_rule_vlan', ['rule_id', 'vlan_id'])


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
        'firewall.firewall': {
            'Meta': {'object_name': 'Firewall'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'rules': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['firewall.Rule']", 'null': 'True', 'blank': 'True'})
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
        'firewall.rule': {
            'Meta': {'object_name': 'Rule'},
            'accept': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'direction': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'dport': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'extra': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'foreign_network': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'ForeignRules'", 'to': "orm['firewall.VlanGroup']"}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['firewall.Host']", 'null': 'True', 'blank': 'True'}),
            'hostgroup': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['firewall.Group']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'nat': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'nat_dport': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'proto': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'r_type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'sport': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'vlan': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['firewall.Vlan']", 'null': 'True', 'blank': 'True'}),
            'vlangroup': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['firewall.VlanGroup']", 'null': 'True', 'blank': 'True'})
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
