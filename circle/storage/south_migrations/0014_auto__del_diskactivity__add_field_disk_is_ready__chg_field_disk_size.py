# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'DiskActivity'
        db.delete_table(u'storage_diskactivity')

        # Adding field 'Disk.is_ready'
        db.add_column(u'storage_disk', 'is_ready',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


        # Changing field 'Disk.size'
        db.alter_column(u'storage_disk', 'size', self.gf('sizefield.models.FileSizeField')(null=True))

    def backwards(self, orm):
        # Adding model 'DiskActivity'
        db.create_table(u'storage_diskactivity', (
            ('task_uuid', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50, null=True, blank=True)),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(related_name='children', null=True, to=orm['storage.DiskActivity'], blank=True)),
            ('started', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('finished', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('result', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('disk', self.gf('django.db.models.fields.related.ForeignKey')(related_name='activity_log', to=orm['storage.Disk'])),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('activity_code', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('succeeded', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
        ))
        db.send_create_signal(u'storage', ['DiskActivity'])

        # Deleting field 'Disk.is_ready'
        db.delete_column(u'storage_disk', 'is_ready')


        # Changing field 'Disk.size'
        db.alter_column(u'storage_disk', 'size', self.gf('sizefield.models.FileSizeField')(default=None))

    models = {
        u'storage.datastore': {
            'Meta': {'ordering': "[u'name']", 'object_name': 'DataStore'},
            'hostname': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'path': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'})
        },
        u'storage.disk': {
            'Meta': {'ordering': "[u'name']", 'object_name': 'Disk'},
            'base': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'derivatives'", 'null': 'True', 'to': u"orm['storage.Disk']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'datastore': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['storage.DataStore']"}),
            'destroyed': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'dev_num': ('django.db.models.fields.CharField', [], {'default': "u'a'", 'max_length': '1'}),
            'filename': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '256'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_ready': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'size': ('sizefield.models.FileSizeField', [], {'default': 'None', 'null': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '10'})
        }
    }

    complete_apps = ['storage']