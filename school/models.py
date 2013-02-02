from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.core.exceptions import ValidationError
from datetime import datetime

def create_user_profile(sender, instance, created, **kwargs):
    if created:
        try:
            Person.objects.create(user=instance)
        except:
            pass

post_save.connect(create_user_profile, sender=User)

class Person(models.Model):
    user = models.ForeignKey(User, null=False, blank=False, unique=True)

    def __unicode__(self):
        return self.user.__unicode__()

class Course(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=80, null=True, blank=True)
    default_group = models.ForeignKey('Group', null=True, blank=True,
            related_name='default_group_of')
    owners = models.ManyToManyField(User, blank=True, null=True)
    def get_or_create_default_group(self):
            self.default_group = Group(name=self.name,
                    semester=Semester.get_current())
            self.default_group.save()
    def save(self, *args, **kwargs):
        if self.default_group:
            self.default_group.course = self
            self.default_group.save()
        self.full_clean()
        super(Course, self).save(*args, **kwargs)


class Semester(models.Model):
    start = models.DateField()
    end = models.DateField()

    def is_on(self, time):
        return self.start <= time.date() and self.end >= time.date()

    @classmethod
    def get_current(cls):
        n = datetime.now()
        current = [s for s in Semester.objects.all() if s.is_on(n)]
        try:
            return current[0]
        except:
            raise ValidationError(_('There is no current semester.'))


class Group(models.Model):
    name = models.CharField(max_length=80, unique=True)
    course = models.ForeignKey('Course', null=True, blank=True)
    semester = models.ForeignKey('Semester', null=False, blank=False)
    owners = models.ManyToManyField(User, blank=True, null=True, related_name='owned_groups')
    members = models.ManyToManyField(User, blank=True, null=True, related_name='course_groups')

    class Meta:
        unique_together = (('name', 'course', 'semester', ), )
