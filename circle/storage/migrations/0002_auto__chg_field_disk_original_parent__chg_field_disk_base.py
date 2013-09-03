# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Disk.original_parent'
        db.alter_column('storage_disk', 'original_parent_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['storage.Disk'], null=True))

        # Changing field 'Disk.base'
        db.alter_column('storage_disk', 'base_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['storage.Disk']))

    def backwards(self, orm):

        # User chose to not deal with backwards NULL issues for 'Disk.original_parent'
        raise RuntimeError("Cannot reverse this migration. 'Disk.original_parent' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'Disk.base'
        raise RuntimeError("Cannot reverse this migration. 'Disk.base' and its values cannot be restored.")

    models = {
        'storage.disk': {
            'Meta': {'ordering': "['name']", 'object_name': 'Disk'},
            'base': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'snapshots'", 'null': 'True', 'to': "orm['storage.Disk']"}),
            'format': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'original_parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['storage.Disk']", 'null': 'True', 'blank': 'True'}),
            'path': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'}),
            'size': ('django.db.models.fields.IntegerField', [], {}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '10'})
        }
    }

    complete_apps = ['storage']