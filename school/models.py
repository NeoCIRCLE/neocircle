from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.core.exceptions import ValidationError
from datetime import datetime
from django.conf import settings


LANGUAGE_CODE = settings.LANGUAGE_CODE
LANGUAGE_CHOICES = (('hu', _('Hungarian')), ('en', _('English')))

def create_user_profile(sender, instance, created, **kwargs):
    if created:
        try:
            p = Person.objects.get(code=instance.username)
        except Exception:
            p = Person.objects.create(code=instance.username)
        except:
            return
        p.code = instance.username
        p.save()
post_save.connect(create_user_profile, sender=User)

class Person(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, unique=True)
    language = models.CharField(verbose_name=_('language'), blank=False, max_length=10,
            choices=LANGUAGE_CHOICES, default=LANGUAGE_CODE)
    code = models.CharField(_('code'), max_length=30, unique=True)

    def short_name(self):
        if self.user.last_name:
            return self.user.last_name
        else:
            return self.user.username

    def __unicode__(self):
        u = self.user
        if not u:
            return unicode(_("(none)"))
        if u.last_name and u.first_name:
            # TRANSLATORS: full name format used in enumerations
            return _("%(first)s %(last)s") % {'first': u.first_name,
                                             'last': u.last_name}
        else:
            return u.username

    class Meta:
        verbose_name = _('person')
        verbose_name_plural = _('persons')

class Course(models.Model):
    code = models.CharField(max_length=20, unique=True,
            verbose_name=_('course code'))
    name = models.CharField(max_length=80, null=True, blank=True,
            verbose_name=_('name'))
    short_name = models.CharField(max_length=10, null=True, blank=True,
            verbose_name=_('name'))
    default_group = models.ForeignKey('Group', null=True, blank=True,
            related_name='default_group_of', verbose_name=_('default group'),
            help_text=_('New users will automatically get to this group.'))
    owners = models.ManyToManyField(Person, blank=True, null=True,
            verbose_name=_('owners'))

    class Meta:
        verbose_name = _('course')
        verbose_name_plural = _('courses')

    def get_or_create_default_group(self):
        if self.default_group:
            return self.default_group
        else:
            default_group = Group(name=_("%s (auto)") % self.short(),
                    semester=Semester.get_current(), course=self)
            default_group.save()
            self.default_group_id = default_group.id
            self.save()
            return default_group

    def save(self, *args, **kwargs):
        if self.default_group:
            self.default_group.course = self
            self.default_group.save()
        self.full_clean()
        super(Course, self).save(*args, **kwargs)

    def __unicode__(self):
        if self.name:
            return u"%s (%s)" % (self.code, self.name)
        else:
            return self.code

    def short(self):
        if self.short_name:
            return self.short_name
        else:
            return self.code
    short.verbose_name = _('short name')

    def owner_list(self):
        if self.owners and self.owners.count() > 0:
            return ", ".join([p.short_name() for p in self.owners.all()])
        else:
            return _("(none)")
    owner_list.verbose_name = _('owners')


class Semester(models.Model):
    name = models.CharField(max_length=20, unique=True, null=False,
            verbose_name=_('name'))
    start = models.DateField(verbose_name=_('start'))
    end = models.DateField(verbose_name=_('end'))

    class Meta:
        verbose_name = _('semester')
        verbose_name_plural = _('semesters')

    def is_on(self, time):
        return self.start <= time.date() and self.end >= time.date()
    is_on.boolean = True

    @classmethod
    def get_current(cls):
        n = datetime.now()
        current = [s for s in Semester.objects.all() if s.is_on(n)]
        try:
            return current[0]
        except:
            raise ValidationError(_('There is no current semester.'))

    def __unicode__(self):
        return self.name


class Group(models.Model):
    name = models.CharField(max_length=80, verbose_name=_('name'))
    course = models.ForeignKey('Course', null=True, blank=True, verbose_name=_('course'))
    semester = models.ForeignKey('Semester', null=False, blank=False, verbose_name=_('semester'))
    owners = models.ManyToManyField(Person, blank=True, null=True, related_name='owned_groups', verbose_name=_('owners'))
    members = models.ManyToManyField(Person, blank=True, null=True, related_name='course_groups', verbose_name=_('members'))

    class Meta:
        unique_together = (('name', 'course', 'semester', ), )
        verbose_name = _('group')
        verbose_name_plural = _('groups')

    def owner_list(self):
        if self.owners:
            return ", ".join([p.short_name() for p in self.owners.all()])
        else:
            return _("n/a")
    owner_list.verbose_name = _('owners')

    def member_count(self):
        return self.members.count()

    def __unicode__(self):
        if self.course:
            return "%s (%s)" % (self.name, self.course.short())
        else:
            return "%s (%s)" % (self.name, self.owner_list())
