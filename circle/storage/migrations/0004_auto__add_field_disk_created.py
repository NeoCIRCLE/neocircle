# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Disk.created'
        db.add_column('storage_disk', 'created',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Disk.created'
        db.delete_column('storage_disk', 'created')


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
            'created': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
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