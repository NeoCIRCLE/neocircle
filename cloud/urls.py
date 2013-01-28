from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

import one.views
import firewall.views
#import store.views

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
)
