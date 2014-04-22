from django import contrib
# from django.utils.translation import ugettext_lazy as _

from .models import Disk, DataStore, DiskActivity


class DiskAdmin(contrib.admin.ModelAdmin):
    list_display = ('id', 'name', 'base', 'type', 'datastore')
    ordering = ('-id', )


class DataStoreAdmin(contrib.admin.ModelAdmin):
    list_display = ('name', 'path')


contrib.admin.site.register(Disk, DiskAdmin)
contrib.admin.site.register(DiskActivity)
contrib.admin.site.register(DataStore, DataStoreAdmin)
