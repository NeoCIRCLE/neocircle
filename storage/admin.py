from django import contrib
# from django.utils.translation import ugettext_lazy as _

from .models import Disk, DataStore


class DiskAdmin(contrib.admin.ModelAdmin):
    list_display = ('name', 'datastore')


class DataStoreAdmin(contrib.admin.ModelAdmin):
    list_display = ('name', 'path')


contrib.admin.site.register(Disk, DiskAdmin)
contrib.admin.site.register(DataStore, DataStoreAdmin)
