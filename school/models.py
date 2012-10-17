from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.db.models.signals import post_save

def create_user_profile(sender, instance, created, **kwargs):
    if created:
            Person.objects.create(user=instance)

post_save.connect(create_user_profile, sender=User)

LANGS = [('hu', _('Hungarian')), ('en_US', _('US English'))]
class Person(models.Model):
    user = models.ForeignKey(User, null=False, blank=False, unique=True)
    language = models.CharField(max_length=6, choices=LANGS,
            verbose_name=_('Preferred language'))
 
    def __unicode__(self):
        return self.user.__unicode__()

class Entity(models.Model):
    parent = models.ForeignKey('school.Group')
    name = models.CharField(max_length=100)


class Group(Entity):
    recursive_unique = models.BooleanField()

class Course(Entity):
    pass

class Semester(Entity):
    start = models.DateField()
    end = models.DateField()

EVENT_CHOICES = [('free', _('free text')), ('num', _('number')), ('int', _('integer'))]
class Event(models.Model):
    title = models.CharField(max_length=100)
    group = models.ForeignKey('school.Group')
    type = models.CharField(max_length=5, choices=EVENT_CHOICES)

class Mark(models.Model):
    value = models.CharField(max_length=100)
    student = models.ForeignKey('Person')
    event = models.ForeignKey('school.Event')
    created_by = models.ForeignKey('Person', related_name='created_marks')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_by = models.ForeignKey('Person', related_name='modified_marks')
    modified_at = models.DateTimeField(auto_now=True)

class Attendance(models.Model):
    present = models.NullBooleanField()
    student = models.ForeignKey('Person')
    lesson = models.ForeignKey('school.Lesson')
    modified_by = models.ForeignKey('Person',
            related_name='modified_attendances')
    modified_at = models.DateTimeField(auto_now=True)

class LessonClass(models.Model):
    group = models.ForeignKey('school.Group')

class Lesson(models.Model):
    lesson_class = models.ForeignKey('school.LessonClass')
    group = models.ForeignKey('school.Group')
