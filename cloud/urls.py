from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

import one.views

urlpatterns = patterns('',
     url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
     url(r'^admin/', include(admin.site.urls)),
     url(r'^$', 'one.views.home', name='home'),
     url(r'^login/$', 'school.views.login', name='login'),
     url(r'^logout/$', 'school.views.logout', name='logout'),
     url(r'^vm/new/(?P<template>\d+)/$', 'one.views.vm_new', name='vm_new'),
     url(r'^vm/show/(?P<iid>\d+)/$', 'one.views.vm_show', name='vm_show'),
     url(r'^vm/delete/(?P<iid>\d+)/$', 'one.views.vm_delete', name='vm_delete'),
)
