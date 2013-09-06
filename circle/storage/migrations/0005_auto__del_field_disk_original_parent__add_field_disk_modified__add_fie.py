# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from django.utils.timezone import now


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Disk.original_parent'
        db.delete_column(u'storage_disk', 'original_parent_id')

        # Adding field 'Disk.modified'
        db.add_column(u'storage_disk', 'modified',
                      self.gf('model_utils.fields.AutoLastModifiedField')(default=now),
                      keep_default=False)

        # Adding field 'Disk.ready'
        db.add_column(u'storage_disk', 'ready',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'Disk.dev_num'
        db.add_column(u'storage_disk', 'dev_num',
                      self.gf('django.db.models.fields.CharField')(default='a', max_length=1),
                      keep_default=False)


        # Changing field 'Disk.created'
        # db.alter_column(u'storage_disk', 'created', self.gf('model_utils.fields.AutoCreatedField')())
        db.delete_column(u'storage_disk', 'created')
        db.add_column(u'storage_disk', 'created',
                      self.gf('model_utils.fields.AutoLastModifiedField')(default=now),
                      keep_default=False)

    def backwards(self, orm):
        # Adding field 'Disk.original_parent'
        db.add_column(u'storage_disk', 'original_parent',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['storage.Disk'], null=True, blank=True),
                      keep_default=False)

        # Deleting field 'Disk.modified'
        db.delete_column(u'storage_disk', 'modified')

        # Deleting field 'Disk.ready'
        db.delete_column(u'storage_disk', 'ready')

        # Deleting field 'Disk.dev_num'
        db.delete_column(u'storage_disk', 'dev_num')


        # Changing field 'Disk.created'
        # db.alter_column(u'storage_disk', 'created', self.gf('django.db.models.fields.BooleanField')())
        db.delete_column(u'storage_disk', 'created')
        db.add_column(u'storage_disk', 'created',
                      self.gf('django.db.models.fields.BooleanField')(default=True),
                      keep_default=False)

    models = {
        u'storage.datastore': {
            'Meta': {'ordering': "['name']", 'object_name': 'DataStore'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'path': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'})
        },
        u'storage.disk': {
            'Meta': {'ordering': "['name']", 'object_name': 'Disk'},
            'base': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'derivatives'", 'null': 'True', 'to': u"orm['storage.Disk']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'datastore': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['storage.DataStore']"}),
            'dev_num': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'format': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'ready': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'size': ('django.db.models.fields.IntegerField', [], {}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '10'})
        }
    }

    complete_apps = ['storage']
