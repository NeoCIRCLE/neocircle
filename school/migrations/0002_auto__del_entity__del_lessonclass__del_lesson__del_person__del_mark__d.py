# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'Entity'
        db.delete_table('school_entity')

        # Deleting model 'LessonClass'
        db.delete_table('school_lessonclass')

        # Deleting model 'Lesson'
        db.delete_table('school_lesson')

        # Deleting model 'Person'
        db.delete_table('school_person')

        # Deleting model 'Mark'
        db.delete_table('school_mark')

        # Deleting model 'Course'
        db.delete_table('school_course')

        # Deleting model 'Semester'
        db.delete_table('school_semester')

        # Deleting model 'Event'
        db.delete_table('school_event')

        # Deleting model 'Attendance'
        db.delete_table('school_attendance')

        # Deleting model 'Group'
        db.delete_table('school_group')


    def backwards(self, orm):
        # Adding model 'Entity'
        db.create_table('school_entity', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['school.Group'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal('school', ['Entity'])

        # Adding model 'LessonClass'
        db.create_table('school_lessonclass', (
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['school.Group'])),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('school', ['LessonClass'])

        # Adding model 'Lesson'
        db.create_table('school_lesson', (
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['school.Group'])),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('lesson_class', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['school.LessonClass'])),
        ))
        db.send_create_signal('school', ['Lesson'])

        # Adding model 'Person'
        db.create_table('school_person', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('language', self.gf('django.db.models.fields.CharField')(default='hu', max_length=6)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], unique=True)),
        ))
        db.send_create_signal('school', ['Person'])

        # Adding model 'Mark'
        db.create_table('school_mark', (
            ('modified_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='modified_marks', to=orm['school.Person'])),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('student', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['school.Person'])),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('event', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['school.Event'])),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='created_marks', to=orm['school.Person'])),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('school', ['Mark'])

        # Adding model 'Course'
        db.create_table('school_course', (
            ('entity_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['school.Entity'], unique=True, primary_key=True)),
        ))
        db.send_create_signal('school', ['Course'])

        # Adding model 'Semester'
        db.create_table('school_semester', (
            ('entity_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['school.Entity'], unique=True, primary_key=True)),
            ('start', self.gf('django.db.models.fields.DateField')()),
            ('end', self.gf('django.db.models.fields.DateField')()),
        ))
        db.send_create_signal('school', ['Semester'])

        # Adding model 'Event'
        db.create_table('school_event', (
            ('type', self.gf('django.db.models.fields.CharField')(max_length=5)),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['school.Group'])),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal('school', ['Event'])

        # Adding model 'Attendance'
        db.create_table('school_attendance', (
            ('modified_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='modified_attendances', to=orm['school.Person'])),
            ('modified_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('student', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['school.Person'])),
            ('lesson', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['school.Lesson'])),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('present', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
        ))
        db.send_create_signal('school', ['Attendance'])

        # Adding model 'Group'
        db.create_table('school_group', (
            ('entity_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['school.Entity'], unique=True, primary_key=True)),
            ('recursive_unique', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('school', ['Group'])


    models = {
        
    }

    complete_apps = ['school']