# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'DataStore'
        db.create_table('storage_datastore', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('path', self.gf('django.db.models.fields.CharField')(unique=True, max_length=200)),
        ))
        db.send_create_signal('storage', ['DataStore'])

        # Deleting field 'Disk.path'
        db.delete_column('storage_disk', 'path')

        # Adding field 'Disk.datastore'
        db.add_column('storage_disk', 'datastore',
                      self.gf('django.db.models.fields.related.ForeignKey')(default=None, to=orm['storage.DataStore']),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting model 'DataStore'
        db.delete_table('storage_datastore')


        # User chose to not deal with backwards NULL issues for 'Disk.path'
        raise RuntimeError("Cannot reverse this migration. 'Disk.path' and its values cannot be restored.")
        # Deleting field 'Disk.datastore'
        db.delete_column('storage_disk', 'datastore_id')


    models = {
        'storage.datastore': {
            'Meta': {'ordering': "['name']", 'object_name': 'DataStore'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'path': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'})
        },
        'storage.disk': {
            'Meta': {'ordering': "['name']", 'object_name': 'Disk'},
            'base': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'snapshots'", 'null': 'True', 'to': "orm['storage.Disk']"}),
            'datastore': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['storage.DataStore']"}),
            'format': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'original_parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['storage.Disk']", 'null': 'True', 'blank': 'True'}),
            'size': ('django.db.models.fields.IntegerField', [], {}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '10'})
        }
    }

    complete_apps = ['storage']