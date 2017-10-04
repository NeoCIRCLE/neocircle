# Copyright 2014 Budapest University of Technology and Economics (BME IK)
#
# This file is part of CIRCLE Cloud.
#
# CIRCLE is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# CIRCLE is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along
# with CIRCLE.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import
from django.conf.urls import url

from .views import (
    RequestList, RequestDetail, RequestTypeList,
    LeaseTypeCreate, LeaseTypeDetail,
    TemplateAccessTypeCreate, TemplateAccessTypeDetail,
    TemplateRequestView, LeaseRequestView, ResourceRequestView,
    LeaseTypeDelete, TemplateAccessTypeDelete, ResizeRequestView,
)

urlpatterns = [
    url(r'^list/$', RequestList.as_view(),
        name="request.views.request-list"),
    url(r'^(?P<pk>\d+)/$', RequestDetail.as_view(),
        name="request.views.request-detail"),

    url(r'^type/list/$', RequestTypeList.as_view(),
        name="request.views.type-list"),

    # request types
    url(r'^type/lease/create/$', LeaseTypeCreate.as_view(),
        name="request.views.lease-type-create"),
    url(r'^type/lease/(?P<pk>\d+)/$', LeaseTypeDetail.as_view(),
        name="request.views.lease-type-detail"),
    url(r'^type/lease/delete/(?P<pk>\d+)/$', LeaseTypeDelete.as_view(),
        name="request.views.lease-type-delete"),

    url(r'^type/template/create/$', TemplateAccessTypeCreate.as_view(),
        name="request.views.template-type-create"),
    url(r'^type/template/(?P<pk>\d+)/$',
        TemplateAccessTypeDetail.as_view(),
        name="request.views.template-type-detail"),
    url(r'^type/template/delete/(?P<pk>\d+)/$',
        TemplateAccessTypeDelete.as_view(),
        name="request.views.template-type-delete"),

    # request views (visible for users)
    url(r'template/$', TemplateRequestView.as_view(),
        name="request.views.request-template"),
    url(r'lease/(?P<vm_pk>\d+)/$', LeaseRequestView.as_view(),
        name="request.views.request-lease"),
    url(r'resource/(?P<vm_pk>\d+)/$', ResourceRequestView.as_view(),
        name="request.views.request-resource"),
    url(r'resize/(?P<vm_pk>\d+)/(?P<disk_pk>\d+)/$',
        ResizeRequestView.as_view(), name="request.views.request-resize"),
]
