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
    list_display = ('username', 'full_name', 'email', 'date_joined', 'instance_count')
    try:
        inlines = inlines + (PersonInline, SshKeyInline, DetailsInline)
    except NameError:
        inlines = (PersonInline, SshKeyInline, DetailsInline)
    def instance_count(self, obj):
        return obj.instance_set.count()
    def full_name(self, obj):
        return u"%s %s" % (obj.last_name, obj.first_name)
    full_name.admin_order_field = 'last_name'



contrib.admin.site.unregister(contrib.auth.models.User)
contrib.admin.site.register(contrib.auth.models.User, MyUserAdmin)

def update_state(modeladmin, request, queryset):
    for i in queryset.all():
        i.update_state()
update_state.short_description = _('Update status')

def submit_vm(modeladmin, request, queryset):
    for i in queryset.all():
        i.submit(request.user)
submit_vm.short_description = _('Submit VM')


class TemplateAdmin(contrib.admin.ModelAdmin):
    model=models.Template
    list_display = ('name', 'state', owner_person, 'system', 'public')
    list_filter = ('owner', 'public')

class InstanceAdmin(contrib.admin.ModelAdmin):
    model=models.Instance
    actions = [update_state, submit_vm]
    list_display = ('id', 'name', owner_person, 'state')
    readonly_fields = ('ip', 'active_since', 'pw', 'template')
    list_filter = ('owner', 'template', 'state')

class DiskAdmin(contrib.admin.ModelAdmin):
    model=models.Disk
class NetworkAdmin(contrib.admin.ModelAdmin):
    model=models.Network
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

