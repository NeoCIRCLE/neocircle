from django.contrib import messages
from django.core.exceptions import ValidationError
from django import contrib
from django.utils.translation import ugettext_lazy as _
from one import models
import string

def owner_person(obj):
    p = obj.owner
    return "%s %s (%s)" % (p.last_name, p.first_name, p.username)
owner_person.short_description = _('owner')

class PersonInline(contrib.admin.StackedInline):
    model = models.Person
    max_num = 1
    can_delete = False
class SshKeyInline(contrib.admin.TabularInline):
    model = models.SshKey
    extra = 2
class DetailsInline(contrib.admin.StackedInline):
    model = models.UserCloudDetails
    max_num = 1
    can_delete = False

class MyUserAdmin(contrib.auth.admin.UserAdmin):
    list_display = ('username', 'full_name', 'email', 'date_joined', 'instance_count', 'course_groups')
    list_filter = ('is_superuser', 'is_active', 'groups', 'person__course_groups', )

    try:
        inlines = inlines + (PersonInline, SshKeyInline, DetailsInline)
    except NameError:
        inlines = (PersonInline, SshKeyInline, DetailsInline)

    def instance_count(self, obj):
        return _("%(sum)d (%(active)d active)") % { 'sum': obj.instance_set.count(),
                'active' :obj.instance_set.filter(state='ACTIVE').count(), }

    def course_groups(self, obj):
        try:
            return ", ".join(obj.person_set.all()[0].course_groups.all())
        except:
            return None

    def full_name(self, obj):
        return u"%s %s" % (obj.last_name, obj.first_name)
    full_name.admin_order_field = 'last_name'

    ordering = ["-date_joined"]



contrib.admin.site.unregister(contrib.auth.models.User)
contrib.admin.site.register(contrib.auth.models.User, MyUserAdmin)

def update_state(modeladmin, request, queryset):
    for i in queryset.all():
        i.update_state()
update_state.short_description = _('Update status')

def submit_vm(modeladmin, request, queryset):
    for i in queryset.all():
        i.submit(request.user)
        i.update_state()
submit_vm.short_description = _('Submit VM')

def delete_vm(modeladmin, request, queryset):
    for i in queryset.exclude(state='DONE').all():
        i.one_delete()
delete_vm.short_description = _('Delete VM')

def suspend_vm(modeladmin, request, queryset):
    for i in queryset.filter(state='ACTIVE').all():
        i.stop()
suspend_vm.short_description = _('Suspend VM')

def resume_vm(modeladmin, request, queryset):
    for i in queryset.filter(state__in=('STOPPED', 'SUSPENDED')).all():
        i.resume()
resume_vm.short_description = _('Resume VM')


class TemplateAdmin(contrib.admin.ModelAdmin):
    model=models.Template
    list_display = ('name', 'state', owner_person, 'system', 'public')
    list_filter = ('owner', 'public')

class InstanceAdmin(contrib.admin.ModelAdmin):
    model=models.Instance
    actions = [update_state, submit_vm, delete_vm, suspend_vm, resume_vm]
    list_display = ('id', 'name', owner_person, 'state', 'ip')
    readonly_fields = ('ip', 'active_since', 'pw', )
    list_filter = ('state', 'owner', 'template')
    search_fields = ('ip', 'name')
    def queryset(self, request):
        return super(InstanceAdmin, self).queryset(request)

class DiskAdmin(contrib.admin.ModelAdmin):
    model=models.Disk
    list_display = ('name', 'used_by')

    def used_by(self, obj):
        try:
            return ", ".join(obj.template_set.all())
        except:
            return None
    used_by.verbose_name = _('used by')

class NetworkAdmin(contrib.admin.ModelAdmin):
    model=models.Network
    list_display = ('name', 'nat', 'public', 'get_vlan')

class ShareAdmin(contrib.admin.ModelAdmin):
    model=models.Network
    list_filter = ('group', 'template', )
    list_display = ('name', owner_person, 'template', 'group', )

contrib.admin.site.register(models.Template, TemplateAdmin)
contrib.admin.site.register(models.Instance, InstanceAdmin)
contrib.admin.site.register(models.Network, NetworkAdmin)
contrib.admin.site.register(models.Disk, DiskAdmin)
contrib.admin.site.register(models.Share, ShareAdmin)
contrib.admin.site.register(models.InstanceType)

