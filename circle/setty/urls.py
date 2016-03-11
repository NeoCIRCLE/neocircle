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

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^create/$',
        views.CreateView.as_view(),
        name='setty.views.service-create'),
    url(r'^delete/(?P<pk>\d+)$',
        views.DeleteView.as_view(),
        name='setty.views.service-delete'),
    url(r'^start/(?P<pk>\d+)$',
        views.StartView.as_view(),
        name='setty.views.service-start'),
    url(r'^stop/(?P<pk>\d+)$',
        views.StopView.as_view(),
        name='setty.views.service-stop'),
    url(r'^list/$',
        views.ListView.as_view(),
        name='setty.views.service-list'),
    url(r'^(?P<pk>\d+)/$',
        views.DetailView.as_view(),
        name='setty.views.service-detail'),
]
