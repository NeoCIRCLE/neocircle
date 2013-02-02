from django.contrib import messages
from django.core.exceptions import ValidationError
from django import contrib
from django.utils.translation import ugettext_lazy as _
from school import models
import string

class GroupInline(contrib.admin.TabularInline):
    model = models.Group
    extra = 2

class CourseAdmin(contrib.admin.ModelAdmin):
    model=models.Course
    inlines = (GroupInline, )
    filter_horizontal = ('owners', )

class GroupAdmin(contrib.admin.ModelAdmin):
    model = models.Group
    filter_horizontal = ('owners', 'members', )

class SemesterAdmin(contrib.admin.ModelAdmin):
    model=models.Semester

contrib.admin.site.register(models.Course, CourseAdmin)
contrib.admin.site.register(models.Semester, SemesterAdmin)
contrib.admin.site.register(models.Group, GroupAdmin)

