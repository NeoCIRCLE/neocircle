# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Rule'
        db.create_table('firewall_rule', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('direction', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('vlan', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['firewall.Vlan'])),
            ('extra', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('action', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('firewall', ['Rule'])

        # Adding model 'Vlan'
        db.create_table('firewall_vlan', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('vid', self.gf('django.db.models.fields.IntegerField')(unique=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=20)),
            ('prefix4', self.gf('django.db.models.fields.IntegerField')(default=16)),
            ('prefix6', self.gf('django.db.models.fields.IntegerField')(default=80)),
            ('interface', self.gf('django.db.models.fields.CharField')(unique=True, max_length=20)),
            ('net4', self.gf('django.db.models.fields.GenericIPAddressField')(unique=True, max_length=39)),
            ('net6', self.gf('django.db.models.fields.GenericIPAddressField')(unique=True, max_length=39)),
            ('ipv4', self.gf('django.db.models.fields.GenericIPAddressField')(unique=True, max_length=39)),
            ('ipv6', self.gf('django.db.models.fields.GenericIPAddressField')(unique=True, max_length=39)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('comment', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('domain', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('dhcp_pool', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('firewall', ['Vlan'])

        # Adding M2M table for field en_dst on 'Vlan'
        db.create_table('firewall_vlan_en_dst', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('from_vlan', models.ForeignKey(orm['firewall.vlan'], null=False)),
            ('to_vlan', models.ForeignKey(orm['firewall.vlan'], null=False))
        ))
        db.create_unique('firewall_vlan_en_dst', ['from_vlan_id', 'to_vlan_id'])

        # Adding model 'Group'
        db.create_table('firewall_group', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=20)),
        ))
        db.send_create_signal('firewall', ['Group'])

        # Adding M2M table for field rules on 'Group'
        db.create_table('firewall_group_rules', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('group', models.ForeignKey(orm['firewall.group'], null=False)),
            ('rule', models.ForeignKey(orm['firewall.rule'], null=False))
        ))
        db.create_unique('firewall_group_rules', ['group_id', 'rule_id'])

        # Adding model 'Host'
        db.create_table('firewall_host', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('hostname', self.gf('django.db.models.fields.CharField')(unique=True, max_length=20)),
            ('mac', self.gf('firewall.models.MACAddressField')(unique=True, max_length=17)),
            ('ipv4', self.gf('django.db.models.fields.GenericIPAddressField')(unique=True, max_length=39)),
            ('pub_ipv4', self.gf('django.db.models.fields.GenericIPAddressField')(max_length=39, unique=True, null=True, blank=True)),
            ('ipv6', self.gf('django.db.models.fields.GenericIPAddressField')(unique=True, max_length=39)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('comment', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('location', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('vlan', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['firewall.Vlan'])),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
        ))
        db.send_create_signal('firewall', ['Host'])

        # Adding M2M table for field groups on 'Host'
        db.create_table('firewall_host_groups', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('host', models.ForeignKey(orm['firewall.host'], null=False)),
            ('group', models.ForeignKey(orm['firewall.group'], null=False))
        ))
        db.create_unique('firewall_host_groups', ['host_id', 'group_id'])

        # Adding M2M table for field rules on 'Host'
        db.create_table('firewall_host_rules', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('host', models.ForeignKey(orm['firewall.host'], null=False)),
            ('rule', models.ForeignKey(orm['firewall.rule'], null=False))
        ))
        db.create_unique('firewall_host_rules', ['host_id', 'rule_id'])

        # Adding model 'Firewall'
        db.create_table('firewall_firewall', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=20)),
        ))
        db.send_create_signal('firewall', ['Firewall'])

        # Adding M2M table for field rules on 'Firewall'
        db.create_table('firewall_firewall_rules', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('firewall', models.ForeignKey(orm['firewall.firewall'], null=False)),
            ('rule', models.ForeignKey(orm['firewall.rule'], null=False))
        ))
        db.create_unique('firewall_firewall_rules', ['firewall_id', 'rule_id'])


    def backwards(self, orm):
        # Deleting model 'Rule'
        db.delete_table('firewall_rule')

        # Deleting model 'Vlan'
        db.delete_table('firewall_vlan')

        # Removing M2M table for field en_dst on 'Vlan'
        db.delete_table('firewall_vlan_en_dst')

        # Deleting model 'Group'
        db.delete_table('firewall_group')

        # Removing M2M table for field rules on 'Group'
        db.delete_table('firewall_group_rules')

        # Deleting model 'Host'
        db.delete_table('firewall_host')

        # Removing M2M table for field groups on 'Host'
        db.delete_table('firewall_host_groups')

        # Removing M2M table for field rules on 'Host'
        db.delete_table('firewall_host_rules')

        # Deleting model 'Firewall'
        db.delete_table('firewall_firewall')

        # Removing M2M table for field rules on 'Firewall'
        db.delete_table('firewall_firewall_rules')


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
        'firewall.firewall': {
            'Meta': {'object_name': 'Firewall'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'rules': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['firewall.Rule']", 'null': 'True', 'blank': 'True'})
        },
        'firewall.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'rules': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['firewall.Rule']", 'null': 'True', 'blank': 'True'})
        },
        'firewall.host': {
            'Meta': {'object_name': 'Host'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['firewall.Group']", 'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ipv4': ('django.db.models.fields.GenericIPAddressField', [], {'unique': 'True', 'max_length': '39'}),
            'ipv6': ('django.db.models.fields.GenericIPAddressField', [], {'unique': 'True', 'max_length': '39'}),
            'location': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'mac': ('firewall.models.MACAddressField', [], {'unique': 'True', 'max_length': '17'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'pub_ipv4': ('django.db.models.fields.GenericIPAddressField', [], {'max_length': '39', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'rules': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['firewall.Rule']", 'null': 'True', 'blank': 'True'}),
            'vlan': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['firewall.Vlan']"})
        },
        'firewall.rule': {
            'Meta': {'object_name': 'Rule'},
            'action': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'direction': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'extra': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'vlan': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['firewall.Vlan']"})
        },
        'firewall.vlan': {
            'Meta': {'object_name': 'Vlan'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'dhcp_pool': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'domain': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'en_dst': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['firewall.Vlan']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'interface': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'ipv4': ('django.db.models.fields.GenericIPAddressField', [], {'unique': 'True', 'max_length': '39'}),
            'ipv6': ('django.db.models.fields.GenericIPAddressField', [], {'unique': 'True', 'max_length': '39'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'net4': ('django.db.models.fields.GenericIPAddressField', [], {'unique': 'True', 'max_length': '39'}),
            'net6': ('django.db.models.fields.GenericIPAddressField', [], {'unique': 'True', 'max_length': '39'}),
            'prefix4': ('django.db.models.fields.IntegerField', [], {'default': '16'}),
            'prefix6': ('django.db.models.fields.IntegerField', [], {'default': '80'}),
            'vid': ('django.db.models.fields.IntegerField', [], {'unique': 'True'})
        }
    }

    complete_apps = ['firewall']