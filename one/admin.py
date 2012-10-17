from django.contrib import messages
from django.core.exceptions import ValidationError
from django import contrib
from django.utils.translation import ugettext_lazy as _
from one import models
import string

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
    list_display = ('username', 'email', 'is_staff', 'date_joined', 'get_profile')
    try:
        inlines = inlines + (PersonInline, SshKeyInline, DetailsInline)
    except NameError:
        inlines = (PersonInline, SshKeyInline, DetailsInline)



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

class InstanceAdmin(contrib.admin.ModelAdmin):
    model=models.Instance
    actions = [update_state,submit_vm]
    list_display = ['id', 'name', 'owner', 'state']
    readonly_fields = ['ip', 'active_since', 'pw', 'template']
    list_filter = ['owner', 'template', 'state']
contrib.admin.site.register(models.Template, TemplateAdmin)
contrib.admin.site.register(models.Instance, InstanceAdmin)

