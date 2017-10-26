# Copyright 2017 Budapest University of Technology and Economics (BME IK)
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
from occi.views import (OcciLoginView, OcciLogoutView, OcciQueryInterfaceView,
                        OcciComputeView, OcciComputeCollectionView,
                        OcciStorageView, OcciStorageCollectionView,
                        OcciNetworkView, OcciNetworkCollectionView,
                        OcciStoragelinkView, OcciStoragelinkCollectionView,
                        OcciNetworkInterfaceView,
                        OcciNetworkInterfaceCollectionView,)


urlpatterns = [
    url(r'^login/$', OcciLoginView.as_view()),
    url(r'^logout/$', OcciLogoutView.as_view()),
    url(r'^-/$', OcciQueryInterfaceView.as_view()),
    url(r'^compute/$', OcciComputeCollectionView.as_view()),
    url(r'^compute/(?P<id>\d+)/$', OcciComputeView.as_view()),
    url(r'^storage/$', OcciStorageCollectionView.as_view()),
    url(r'^storage/(?P<id>\d+)/$', OcciStorageView.as_view()),
    url(r'^network/$', OcciNetworkCollectionView.as_view()),
    url(r'^network/(?P<id>\d+)/$', OcciNetworkView.as_view()),
    url(r'^storagelink/$', OcciStoragelinkCollectionView.as_view()),
    url(r'^storagelink/compute(?P<computeid>\d+)-storage(?P<storageid>\d+)/$',
        OcciStoragelinkView.as_view()),
    url(r'^networkinterface/$', OcciNetworkInterfaceCollectionView.as_view()),
    url(r'^networkinterface/compute(?P<computeid>\d+)-network(?P<networkid>' +
        r'\d+)/$',
        OcciNetworkInterfaceView.as_view()),
]
