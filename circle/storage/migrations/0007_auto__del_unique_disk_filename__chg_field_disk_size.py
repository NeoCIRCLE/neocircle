# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'Disk', fields ['filename']
        db.delete_unique(u'storage_disk', ['filename'])


        # Changing field 'Disk.size'
        db.alter_column(u'storage_disk', 'size', self.gf('sizefield.models.FileSizeField')())

    def backwards(self, orm):
        # Adding unique constraint on 'Disk', fields ['filename']
        db.create_unique(u'storage_disk', ['filename'])


        # Changing field 'Disk.size'
        db.alter_column(u'storage_disk', 'size', self.gf('django.db.models.fields.IntegerField')())

    models = {
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
            'dev_num': ('django.db.models.fields.CharField', [], {'default': "'a'", 'max_length': '1'}),
            'filename': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'ready': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'size': ('sizefield.models.FileSizeField', [], {}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '10'})
        }
    }

    complete_apps = ['storage']