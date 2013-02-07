from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

import one.views
import firewall.views
#import store.views

js_info_dict = {
            'packages': ('one', ),
}

urlpatterns = patterns('',
     url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
     url(r'^admin/', include(admin.site.urls)),
     url(r'^$', 'one.views.home', name='home'),
     url(r'^login/$', 'school.views.login', name='login'),
     url(r'^logout/$', 'school.views.logout', name='logout'),
     url(r'^vm/new/(?P<template>\d+)/$', 'one.views.vm_new', name='vm_new'),
     url(r'^vm/show/(?P<iid>\d+)/$', 'one.views.vm_show', name='vm_show'),
     url(r'^vm/delete/(?P<iid>\d+)/$', 'one.views.vm_delete', name='vm_delete'),
     url(r'^vm/stop/(?P<iid>\d+)/$', 'one.views.vm_stop', name='vm_stop'),
     url(r'^vm/resume/(?P<iid>\d+)/$', 'one.views.vm_resume', name='vm_resume'),
     url(r'^vm/power_off/(?P<iid>\d+)/$', 'one.views.vm_power_off', name='vm_power_off'),
     url(r'^vm/restart/(?P<iid>\d+)/$', 'one.views.vm_restart', name='vm_restart'),
     url(r'^vm/port_add/(?P<iid>\d+)/$', 'one.views.vm_port_add', name='vm_port_add'),
     url(r'^vm/port_del/(?P<iid>\d+)/(?P<proto>tcp|udp)/(?P<public>\d+)/$', 'one.views.vm_port_del', name='vm_port_del'),
     url(r'^reload/$', 'firewall.views.reload_firewall', name='reload_firewall'),
     url(r'^fwapi/$', 'firewall.views.firewall_api', name='firewall_api'),
     url(r'^store/$', 'store.views.index', name='store_index'),
     url(r'^store/gui/$', 'store.views.gui', name='store_gui'),
     url(r'^store/top/$', 'store.views.toplist', name='store_top'),
     url(r'^ajax/templateWizard$', 'one.views.ajax_template_wizard', name='ajax_template_wizard'),
     url(r'^ajax/store/list$', 'store.views.ajax_listfolder', name='store_ajax_listfolder'),
     url(r'^ajax/store/download$', 'store.views.ajax_download', name='store_ajax_download'),
     url(r'^ajax/store/upload$', 'store.views.ajax_upload', name='store_ajax_upload'),
     url(r'^ajax/store/delete$', 'store.views.ajax_delete', name='store_ajax_delete'),
     url(r'^ajax/store/newFolder$', 'store.views.ajax_new_folder', name='store_ajax_new_folder'),
     url(r'^ajax/store/quota$', 'store.views.ajax_quota', name='store_ajax_quota'),
     url(r'^ajax/store/rename$', 'store.views.ajax_rename', name='store_ajax_rename'),
     url(r'^ajax/vm/status/(?P<iid>\d+)$', 'one.views.vm_ajax_instance_status', name='vm_ajax_instance_status'),
     url(r'^language/(?P<lang>[-A-Za-z]+)/$', 'school.views.language', name='language'),
     url(r'^jsi18n/$', 'django.views.i18n.javascript_catalog', js_info_dict),
)
