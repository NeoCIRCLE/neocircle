# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Person'
        pass

    def backwards(self, orm):
        # Deleting model 'Person'
        db.delete_table('school_person')

        # Deleting model 'Entity'
        db.delete_table('school_entity')

        # Deleting model 'Group'
        db.delete_table('school_group')

        # Deleting model 'Course'
        db.delete_table('school_course')

        # Deleting model 'Semester'
        db.delete_table('school_semester')

        # Deleting model 'Event'
        db.delete_table('school_event')

        # Deleting model 'Mark'
        db.delete_table('school_mark')

        # Deleting model 'Attendance'
        db.delete_table('school_attendance')

        # Deleting model 'LessonClass'
        db.delete_table('school_lessonclass')

        # Deleting model 'Lesson'
        db.delete_table('school_lesson')


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
        'school.attendance': {
            'Meta': {'object_name': 'Attendance'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lesson': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['school.Lesson']"}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'modified_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'modified_attendances'", 'to': "orm['school.Person']"}),
            'present': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['school.Person']"})
        },
        'school.course': {
            'Meta': {'object_name': 'Course', '_ormbases': ['school.Entity']},
            'entity_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['school.Entity']", 'unique': 'True', 'primary_key': 'True'})
        },
        'school.entity': {
            'Meta': {'object_name': 'Entity'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['school.Group']"})
        },
        'school.event': {
            'Meta': {'object_name': 'Event'},
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['school.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '5'})
        },
        'school.group': {
            'Meta': {'object_name': 'Group', '_ormbases': ['school.Entity']},
            'entity_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['school.Entity']", 'unique': 'True', 'primary_key': 'True'}),
            'recursive_unique': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'school.lesson': {
            'Meta': {'object_name': 'Lesson'},
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['school.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lesson_class': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['school.LessonClass']"})
        },
        'school.lessonclass': {
            'Meta': {'object_name': 'LessonClass'},
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['school.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'school.mark': {
            'Meta': {'object_name': 'Mark'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'created_marks'", 'to': "orm['school.Person']"}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['school.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'modified_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'modified_marks'", 'to': "orm['school.Person']"}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['school.Person']"}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'school.person': {
            'Meta': {'object_name': 'Person'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'default': "'hu'", 'max_length': '6'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'school.semester': {
            'Meta': {'object_name': 'Semester', '_ormbases': ['school.Entity']},
            'end': ('django.db.models.fields.DateField', [], {}),
            'entity_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['school.Entity']", 'unique': 'True', 'primary_key': 'True'}),
            'start': ('django.db.models.fields.DateField', [], {})
        }
    }

    complete_apps = ['school']
