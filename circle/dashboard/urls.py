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
from django.conf.urls import patterns, url, include

import autocomplete_light
from vm.models import Instance
from .views import (
    AclUpdateView, FavouriteView, GroupAclUpdateView, GroupDelete,
    GroupDetailView, GroupList, IndexView,
    InstanceActivityDetail, LeaseCreate, LeaseDelete, LeaseDetail,
    MyPreferencesView, NodeAddTraitView, NodeCreate, NodeDelete,
    NodeDetailView, NodeList,
    NotificationView, TemplateAclUpdateView, TemplateCreate,
    TemplateDelete, TemplateDetail, TemplateList,
    vm_activity, VmCreate, VmDetailView,
    VmDetailVncTokenView, VmList,
    DiskRemoveView, get_disk_download_status,
    GroupRemoveUserView,
    GroupRemoveFutureUserView,
    GroupCreate, GroupProfileUpdate,
    TemplateChoose,
    UserCreationView,
    get_vm_screenshot,
    ProfileView, toggle_use_gravatar, UnsubscribeFormView,
    UserKeyDelete, UserKeyDetail, UserKeyCreate,
    ConnectCommandDelete, ConnectCommandDetail, ConnectCommandCreate,
    StoreList, store_download, store_upload, store_get_upload_url, StoreRemove,
    store_new_directory, store_refresh_toplist,
    VmTraitsUpdate, VmRawDataUpdate, VmDataStoreUpdate,
    GroupPermissionsView,
    LeaseAclUpdateView,
    toggle_template_tutorial,
    ClientCheck, TokenLogin,
    VmGraphView, NodeGraphView, NodeListGraphView, TemplateGraphView,
    TransferInstanceOwnershipView, TransferInstanceOwnershipConfirmView,
    TransferTemplateOwnershipView, TransferTemplateOwnershipConfirmView,
    OpenSearchDescriptionView,
    NodeActivityView,
    UserList,
    StorageDetail, StorageList, StorageChoose, StorageCreate, DiskDetail,
    DataStoreHostCreate,
    MessageList, MessageDetail, MessageCreate, MessageDelete,
)
from .views.vm import vm_ops, vm_mass_ops
from .views.node import node_ops

autocomplete_light.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^$', IndexView.as_view(), name="dashboard.index"),
    url(r"^profile/list/$", UserList.as_view(),
        name="dashboard.views.user-list"),
    url(r'^profile/create/$',
        UserCreationView.as_view(),
        name="dashboard.views.user-create"),
    url(r'^lease/(?P<pk>\d+)/$', LeaseDetail.as_view(),
        name="dashboard.views.lease-detail"),
    url(r'^lease/create/$', LeaseCreate.as_view(),
        name="dashboard.views.lease-create"),
    url(r'^lease/delete/(?P<pk>\d+)/$', LeaseDelete.as_view(),
        name="dashboard.views.lease-delete"),
    url(r'^lease/(?P<pk>\d+)/acl/$', LeaseAclUpdateView.as_view(),
        name="dashboard.views.lease-acl"),

    url(r'^template/create/$', TemplateCreate.as_view(),
        name="dashboard.views.template-create"),
    url(r'^template/choose/$', TemplateChoose.as_view(),
        name="dashboard.views.template-choose"),
    url(r'template/(?P<pk>\d+)/acl/$', TemplateAclUpdateView.as_view(),
        name='dashboard.views.template-acl'),
    url(r'^template/(?P<pk>\d+)/$', TemplateDetail.as_view(),
        name='dashboard.views.template-detail'),
    url(r"^template/list/$", TemplateList.as_view(),
        name="dashboard.views.template-list"),
    url(r"^template/delete/(?P<pk>\d+)/$", TemplateDelete.as_view(),
        name="dashboard.views.template-delete"),
    url(r'^template/(?P<pk>\d+)/tx/$', TransferTemplateOwnershipView.as_view(),
        name='dashboard.views.template-transfer-ownership'),
    url(r'^vm/(?P<pk>\d+)/$', VmDetailView.as_view(),
        name='dashboard.views.detail'),
    url(r'^vm/(?P<pk>\d+)/vnctoken/$', VmDetailVncTokenView.as_view(),
        name='dashboard.views.detail-vnc'),
    url(r'^vm/(?P<pk>\d+)/acl/$', AclUpdateView.as_view(model=Instance),
        name='dashboard.views.vm-acl'),
    url(r'^vm/(?P<pk>\d+)/tx/$', TransferInstanceOwnershipView.as_view(),
        name='dashboard.views.vm-transfer-ownership'),
    url(r'^vm/list/$', VmList.as_view(), name='dashboard.views.vm-list'),
    url(r'^vm/create/$', VmCreate.as_view(),
        name='dashboard.views.vm-create'),
    url(r'^vm/(?P<pk>\d+)/activity/$', vm_activity,
        name='dashboard.views.vm-activity-list'),
    url(r'^vm/activity/(?P<pk>\d+)/$', InstanceActivityDetail.as_view(),
        name='dashboard.views.vm-activity'),
    url(r'^vm/(?P<pk>\d+)/screenshot/$', get_vm_screenshot,
        name='dashboard.views.vm-get-screenshot'),
    url(r'^vm/(?P<pk>\d+)/traits/$', VmTraitsUpdate.as_view(),
        name='dashboard.views.vm-traits'),
    url(r'^vm/(?P<pk>\d+)/raw_data/$', VmRawDataUpdate.as_view(),
        name='dashboard.views.vm-raw-data'),
    url(r'^vm/(?P<pk>\d+)/data_store/$', VmDataStoreUpdate.as_view(),
        name='dashboard.views.vm-data-store'),
    url(r'^vm/(?P<pk>\d+)/toggle_tutorial/$', toggle_template_tutorial,
        name='dashboard.views.vm-toggle-tutorial'),

    url(r'^node/list/$', NodeList.as_view(), name='dashboard.views.node-list'),
    url(r'^node/(?P<pk>\d+)/$', NodeDetailView.as_view(),
        name='dashboard.views.node-detail'),
    url(r'^node/(?P<pk>\d+)/add-trait/$', NodeAddTraitView.as_view(),
        name='dashboard.views.node-addtrait'),
    url(r'^vm/tx/(?P<key>.*)/?$',
        TransferInstanceOwnershipConfirmView.as_view(),
        name='dashboard.views.vm-transfer-ownership-confirm'),
    url(r'^template/tx/(?P<key>.*)/?$',
        TransferTemplateOwnershipConfirmView.as_view(),
        name='dashboard.views.template-transfer-ownership-confirm'),
    url(r'^node/delete/(?P<pk>\d+)/$', NodeDelete.as_view(),
        name="dashboard.views.delete-node"),
    url(r'^node/(?P<pk>\d+)/activity/$', NodeActivityView.as_view(),
        name='dashboard.views.node-activity-list'),
    url(r'^node/create/$', NodeCreate.as_view(),
        name='dashboard.views.node-create'),

    url(r'^favourite/$', FavouriteView.as_view(),
        name='dashboard.views.favourite'),
    url(r'^group/delete/(?P<pk>\d+)/$', GroupDelete.as_view(),
        name="dashboard.views.delete-group"),
    url(r'^group/list/$', GroupList.as_view(),
        name='dashboard.views.group-list'),
    url((r'^vm/(?P<pk>\d+)/graph/(?P<metric>[a-z]+)/'
         r'(?P<time>[0-9]{1,2}[hdwy])$'),
        VmGraphView.as_view(),
        name='dashboard.views.vm-graph'),
    url((r'^node/(?P<pk>\d+)/graph/(?P<metric>[a-z]+)/'
         r'(?P<time>[0-9]{1,2}[hdwy])$'),
        NodeGraphView.as_view(),
        name='dashboard.views.node-graph'),
    url((r'^node/graph/(?P<metric>[a-z]+)/'
         r'(?P<time>[0-9]{1,2}[hdwy])$'),
        NodeListGraphView.as_view(),
        name='dashboard.views.node-list-graph'),
    url((r'^template/(?P<pk>\d+)/graph/(?P<metric>[a-z]+)/'
         r'(?P<time>[0-9]{1,2}[hdwy])$'),
        TemplateGraphView.as_view(),
        name='dashboard.views.template-graph'),
    url(r'^group/(?P<pk>\d+)/$', GroupDetailView.as_view(),
        name='dashboard.views.group-detail'),
    url(r'^group/(?P<pk>\d+)/update/$', GroupProfileUpdate.as_view(),
        name='dashboard.views.group-update'),
    url(r'^group/(?P<pk>\d+)/acl/$', GroupAclUpdateView.as_view(),
        name='dashboard.views.group-acl'),
    url(r'^notifications/$', NotificationView.as_view(),
        name="dashboard.views.notifications"),

    url(r'^disk/(?P<pk>\d+)/remove/$', DiskRemoveView.as_view(),
        name="dashboard.views.disk-remove"),
    url(r'^disk/(?P<pk>\d+)/status/$', get_disk_download_status,
        name="dashboard.views.disk-status"),

    url(r'^profile/$', MyPreferencesView.as_view(),
        name="dashboard.views.profile-preferences"),
    url(r'^subscribe/(?P<token>.*)/$', UnsubscribeFormView.as_view(),
        name="dashboard.views.unsubscribe"),
    url(r'^profile/(?P<username>[^/]+)/$', ProfileView.as_view(),
        name="dashboard.views.profile"),
    url(r'^profile/(?P<username>[^/]+)/use_gravatar/$', toggle_use_gravatar),

    url(r'^group/(?P<group_pk>\d+)/remove/user/(?P<member_pk>\d+)/$',
        GroupRemoveUserView.as_view(),
        name="dashboard.views.remove-user"),
    url(r'^group/(?P<group_pk>\d+)/remove/futureuser/(?P<member_org_id>.+)/$',
        GroupRemoveFutureUserView.as_view(),
        name="dashboard.views.remove-future-user"),
    url(r'^group/create/$', GroupCreate.as_view(),
        name='dashboard.views.group-create'),
    url(r'^group/(?P<group_pk>\d+)/permissions/$',
        GroupPermissionsView.as_view(),
        name="dashboard.views.group-permissions"),

    url(r'^sshkey/delete/(?P<pk>\d+)/$',
        UserKeyDelete.as_view(),
        name="dashboard.views.userkey-delete"),
    url(r'^sshkey/(?P<pk>\d+)/$',
        UserKeyDetail.as_view(),
        name="dashboard.views.userkey-detail"),
    url(r'^sshkey/create/$',
        UserKeyCreate.as_view(),
        name="dashboard.views.userkey-create"),

    url(r'^conncmd/delete/(?P<pk>\d+)/$',
        ConnectCommandDelete.as_view(),
        name="dashboard.views.connect-command-delete"),
    url(r'^conncmd/(?P<pk>\d+)/$',
        ConnectCommandDetail.as_view(),
        name="dashboard.views.connect-command-detail"),
    url(r'^conncmd/create/$',
        ConnectCommandCreate.as_view(),
        name="dashboard.views.connect-command-create"),

    url(r'^autocomplete/', include('autocomplete_light.urls')),

    url(r"^store/list/$", StoreList.as_view(),
        name="dashboard.views.store-list"),
    url(r"^store/download/$", store_download,
        name="dashboard.views.store-download"),
    url(r"^store/upload/url$", store_get_upload_url,
        name="dashboard.views.store-upload-url"),
    url(r"^store/upload/$", store_upload,
        name="dashboard.views.store-upload"),
    url(r"^store/remove/$", StoreRemove.as_view(),
        name="dashboard.views.store-remove"),
    url(r"^store/new_directory/$", store_new_directory,
        name="dashboard.views.store-new-directory"),
    url(r"^store/refresh_toplist$", store_refresh_toplist,
        name="dashboard.views.store-refresh-toplist"),
    url(r"^client/check$", ClientCheck.as_view(),
        name="dashboard.views.client-check"),
    url(r'^token-login/(?P<token>.*)/$', TokenLogin.as_view(),
        name="dashboard.views.token-login"),
    url(r'^vm/opensearch.xml$', OpenSearchDescriptionView.as_view(),
        name="dashboard.views.vm-opensearch"),

    url(r'^storage/create/(?P<type>.+)$', StorageCreate.as_view(),
        name="dashboard.views.storage-create"),
    url(r'^storage/(?P<pk>\d+)/$', StorageDetail.as_view(),
        name='dashboard.views.storage-detail'),
    url(r'^storage/list/$', StorageList.as_view(),
        name="dashboard.views.storage-list"),
    url(r'^storage/choose/$', StorageChoose.as_view(),
        name="dashboard.views.storage-choose"),

    url(r'^storage/host/create/$', DataStoreHostCreate.as_view(),
        name="dashboard.views.storage-host-create"),

    url(r'^disk/(?P<pk>\d+)/$', DiskDetail.as_view(),
        name="dashboard.views.disk-detail"),

    url(r'^message/list/$', MessageList.as_view(),
        name="dashboard.views.message-list"),
    url(r'^message/(?P<pk>\d+)/$', MessageDetail.as_view(),
        name="dashboard.views.message-detail"),
    url(r'^message/create/$', MessageCreate.as_view(),
        name="dashboard.views.message-create"),
    url(r'^message/delete/(?P<pk>\d+)/$', MessageDelete.as_view(),
        name="dashboard.views.message-delete"),
)

urlpatterns += patterns(
    '',
    *(url(r'^vm/(?P<pk>\d+)/op/%s/$' % op, v.as_view(), name=v.get_urlname())
        for op, v in vm_ops.iteritems())
)

urlpatterns += patterns(
    '',
    *(url(r'^vm/mass_op/%s/$' % op, v.as_view(), name=v.get_urlname())
        for op, v in vm_mass_ops.iteritems())
)

urlpatterns += patterns(
    '',
    *(url(r'^node/(?P<pk>\d+)/op/%s/$' % op, v.as_view(), name=v.get_urlname())
        for op, v in node_ops.iteritems())
)
