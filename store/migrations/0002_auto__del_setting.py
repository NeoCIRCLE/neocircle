# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'Setting'
        db.delete_table('store_setting')


    def backwards(self, orm):
        # Adding model 'Setting'
        db.create_table('store_setting', (
            ('value', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=32)),
        ))
        db.send_create_signal('store', ['Setting'])


    models = {
        
    }

    complete_apps = ['store']