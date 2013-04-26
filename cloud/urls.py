from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

import one.views
import firewall.views
# import store.views

js_info_dict = {
    'packages': ('one', ),
}

urlpatterns = patterns('',
    url(r'^admin/doc/', include('django.contrib.admindocs.urls'), ),
    url(r'^admin/', include(admin.site.urls), ),


    url(r'^login/$', 'school.views.login', name='login', ),
    url(r'^logout/$', 'school.views.logout', name='logout', ),

    url(r'^$', 'one.views.index', ),
    url(r'^info/$', 'one.views.info', ),
    url(r'^home/$', 'one.views.home', ),
    url(r'^vm/new/(?P<template>\d+)/$', 'one.views.vm_new',
        name='new_vm_from_template'),
    url(r'^ajax/vm/new/(?P<template>\d+)/$', 'one.views.vm_new_ajax', ),
    url(r'^vm/new/s(?P<share>\d+)/$', 'one.views.vm_new',
        name='new_vm_form_share'),
    url(r'^vm/show/(?P<iid>\d+)/$', 'one.views.vm_show', ),
    url(r'^vm/delete/(?P<iid>\d+)/$', 'one.views.vm_delete', ),
    url(r'^vm/stop/(?P<iid>\d+)/$', 'one.views.vm_stop', ),
    url(r'^vm/unshare/(?P<id>\d+)/$', 'one.views.vm_unshare', ),
    url(r'^vm/resume/(?P<iid>\d+)/$', 'one.views.vm_resume', ),
    url(r'^vm/power_off/(?P<iid>\d+)/$', 'one.views.vm_power_off', ),
    url(r'^vm/restart/(?P<iid>\d+)/$', 'one.views.vm_restart', ),
    url(r'^vm/renew/(?P<which>(suspend|delete))/(?P<iid>\d+)/$',
        'one.views.vm_renew', ),
    url(r'^vm/port_add/(?P<iid>\d+)/$', 'one.views.vm_port_add', ),
    url(r'^vm/port_del/(?P<iid>\d+)/(?P<proto>tcp|udp)/(?P<private>\d+)/$',
        'one.views.vm_port_del', ),
    url(r'^ajax/shareEdit/(?P<id>\d+)/$', 'one.views.ajax_share_edit_wizard',
        name='ajax_share_edit_wizard'),
    url(r'^vm/saveas/(?P<vmid>\d+)$', 'one.views.vm_saveas', ),
    url(r'^vm/credentials/(?P<iid>\d+)$', 'one.views.vm_credentials', ),
    url(r'^ajax/templateWizard/$', 'one.views.ajax_template_wizard', ),
    url(r'^ajax/templateEditWizard/(?P<id>\d+)/$', 'one.views.ajax_template_edit_wizard', ),
    url(r'^ajax/share/(?P<id>\d+)/$', 'one.views.ajax_share_wizard', ),
    url(r'^ajax/share/(?P<id>\d+)/(?P<gid>\d+)$',
        'one.views.ajax_share_wizard', ),
    url(r'^ajax/vm/status/(?P<iid>\d+)$',
        'one.views.vm_ajax_instance_status', ),
    url(r'^ajax/vm/rename/(?P<iid>\d+)/$',
        'one.views.vm_ajax_rename', ),
    url(r'^key/add/$', 'one.views.key_add', ),
    url(r'^ajax/key/delete/$', 'one.views.key_ajax_delete', ),
    url(r'^ajax/key/reset/$', 'one.views.key_ajax_reset', ),
    url(r'^ajax/template/delete/$', 'one.views.ajax_template_delete', ),
    url(r'^ajax/template_name_unique/$',
        'one.views.ajax_template_name_unique', ),

    url(r'^reload/$', 'firewall.views.reload_firewall', ),
    url(r'^fwapi/$', 'firewall.views.firewall_api', ),

    url(r'^store/$', 'store.views.index', ),
    url(r'^store/gui/$', 'store.views.gui', ),
    url(r'^store/top/$', 'store.views.toplist', ),
    url(r'^ajax/store/top/$', 'store.views.ajax_toplist', ),
    url(r'^ajax/store/list$', 'store.views.ajax_listfolder', ),
    url(r'^ajax/store/download$', 'store.views.ajax_download', ),
    url(r'^ajax/store/upload$', 'store.views.ajax_upload', ),
    url(r'^ajax/store/delete$', 'store.views.ajax_delete', ),
    url(r'^ajax/store/newFolder$', 'store.views.ajax_new_folder', ),
    url(r'^ajax/store/quota$', 'store.views.ajax_quota', ),
    url(r'^ajax/store/rename$', 'store.views.ajax_rename', ),

    url(r'^language/(?P<lang>[-A-Za-z]+)/$', 'school.views.language', ),
    url(r'^jsi18n/$', 'django.views.i18n.javascript_catalog', js_info_dict, ),
    url(r'^b/(?P<token>.*)/$', 'one.views.boot_token', ),
    url(r'^group/show/(?P<gid>\d+)/$', 'school.views.group_show',
        name='group_show'),
    url(r'^group/new/$', 'school.views.group_new', ),
    url(r'^ajax/group/(?P<gid>\d+)/add/$',
        'school.views.group_ajax_add_new_member', ),
    url(r'^ajax/group/(?P<gid>\d+)/addOwner/$',
        'school.views.group_ajax_add_new_owner', ),
    url(r'^ajax/group/(?P<gid>\d+)/remove/$',
        'school.views.group_ajax_remove_member', ),
    url(r'^ajax/group/delete/$', 'school.views.group_ajax_delete', ),
    url(r'^ajax/group/autocomplete/$',
        'school.views.group_ajax_owner_autocomplete', ),
    url(r'^stat/$', 'one.views.stat'),
    url(r'^sites/(?P<site>[a-zA-Z0-9]+)/$', 'one.views.sites'),
    url(r'^accounts/(?P<site>profile)/$', 'one.views.sites'),

    url(r'^firewall/$', 'firewall_gui.views.index'),
    url(r'^firewall/rules/$', 'firewall_gui.views.list_rules'),
    url(r'^firewall/hosts/$', 'firewall_gui.views.list_hosts'),
)
