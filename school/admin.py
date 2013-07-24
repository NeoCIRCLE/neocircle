from django import contrib
from school import models


class GroupInline(contrib.admin.TabularInline):
    model = models.Group
    extra = 3


class CourseAdmin(contrib.admin.ModelAdmin):
    model = models.Course
    inlines = (GroupInline, )
    filter_horizontal = ('owners', )
    list_display = ('code', 'name', 'short_name', 'owner_list')
    list_editable = ('name', 'short_name')


class GroupAdmin(contrib.admin.ModelAdmin):
    model = models.Group
    filter_horizontal = ('owners', 'members', )
    list_display = ('name', 'course', 'semester', 'owner_list', 'member_count')
    list_filter = ('semester', 'course')


class SemesterAdmin(contrib.admin.ModelAdmin):
    model = models.Semester
    list_display = ('id', 'name', 'start', 'end')
    list_editable = ('name', 'start', 'end')


contrib.admin.site.register(models.Course, CourseAdmin)
contrib.admin.site.register(models.Semester, SemesterAdmin)
contrib.admin.site.register(models.Group, GroupAdmin)
