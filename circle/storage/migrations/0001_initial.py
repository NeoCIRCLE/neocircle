# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Disk'
        db.create_table('storage_disk', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('path', self.gf('django.db.models.fields.CharField')(unique=True, max_length=200)),
            ('format', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('size', self.gf('django.db.models.fields.IntegerField')()),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('base', self.gf('django.db.models.fields.related.ForeignKey')(related_name='snapshots', to=orm['storage.Disk'])),
            ('original_parent', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['storage.Disk'])),
        ))
        db.send_create_signal('storage', ['Disk'])


    def backwards(self, orm):
        # Deleting model 'Disk'
        db.delete_table('storage_disk')


    models = {
        'storage.disk': {
            'Meta': {'ordering': "['name']", 'object_name': 'Disk'},
            'base': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'snapshots'", 'to': "orm['storage.Disk']"}),
            'format': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'original_parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['storage.Disk']"}),
            'path': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'}),
            'size': ('django.db.models.fields.IntegerField', [], {}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '10'})
        }
    }

    complete_apps = ['storage']