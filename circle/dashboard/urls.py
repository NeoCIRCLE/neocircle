from django.conf.urls import patterns, url

from vm.models import Instance
from .views import (
    AclUpdateView, DiskAddView, FavouriteView, GroupAclUpdateView, GroupDelete,
    GroupDetailView, GroupList, GroupUserDelete, IndexView, LeaseCreate,
    LeaseDelete, LeaseDetail, MyPreferencesView, NodeAddTraitView, NodeCreate,
    NodeDelete, NodeDetailView, NodeGraphView, NodeList, NodeStatus,
    NotificationView, PortDelete, TemplateAclUpdateView, TemplateCreate,
    TemplateDelete, TemplateDetail, TemplateList, TransferOwnershipConfirmView,
    TransferOwnershipView, vm_activity, VmCreate, VmDelete, VmDetailView,
    VmDetailVncTokenView, VmGraphView, VmList, VmMassDelete, VmMigrateView,
    VmRenewView, DiskRemoveView
)

urlpatterns = patterns(
    '',
    url(r'^$', IndexView.as_view(), name="dashboard.index"),
    url(r'^lease/(?P<pk>\d+)/$', LeaseDetail.as_view(),
        name="dashboard.views.lease-detail"),
    url(r'^lease/create/$', LeaseCreate.as_view(),
        name="dashboard.views.lease-create"),
    url(r'^lease/delete/(?P<pk>\d+)/$', LeaseDelete.as_view(),
        name="dashboard.views.lease-delete"),

    url(r'^template/create/$', TemplateCreate.as_view(),
        name="dashboard.views.template-create"),
    url(r'template/(?P<pk>\d+)/acl/$', TemplateAclUpdateView.as_view(),
        name='dashboard.views.template-acl'),
    url(r'^template/(?P<pk>\d+)/$', TemplateDetail.as_view(),
        name='dashboard.views.template-detail'),
    url(r"^template/list/$", TemplateList.as_view(),
        name="dashboard.views.template-list"),
    url(r"^template/delete/(?P<pk>\d+)/$", TemplateDelete.as_view(),
        name="dashboard.views.template-delete"),

    url(r'^vm/(?P<pk>\d+)/remove_port/(?P<rule>\d+)/$', PortDelete.as_view(),
        name='dashboard.views.remove-port'),
    url(r'^vm/(?P<pk>\d+)/$', VmDetailView.as_view(),
        name='dashboard.views.detail'),
    url(r'^vm/(?P<pk>\d+)/vnctoken/$', VmDetailVncTokenView.as_view(),
        name='dashboard.views.detail-vnc'),
    url(r'^vm/(?P<pk>\d+)/acl/$', AclUpdateView.as_view(model=Instance),
        name='dashboard.views.vm-acl'),
    url(r'^vm/(?P<pk>\d+)/tx/$', TransferOwnershipView.as_view(),
        name='dashboard.views.vm-transfer-ownership'),
    url(r'^vm/list/$', VmList.as_view(), name='dashboard.views.vm-list'),
    url(r'^vm/create/$', VmCreate.as_view(),
        name='dashboard.views.vm-create'),
    url(r'^vm/delete/(?P<pk>\d+)/$', VmDelete.as_view(),
        name="dashboard.views.delete-vm"),
    url(r'^vm/mass-delete/', VmMassDelete.as_view(),
        name='dashboard.view.mass-delete-vm'),
    url(r'^vm/(?P<pk>\d+)/activity/$', vm_activity),
    url(r'^vm/(?P<pk>\d+)/migrate/$', VmMigrateView.as_view(),
        name='dashboard.views.vm-migrate'),
    url(r'^vm/(?P<pk>\d+)/renew/((?P<key>.*)/?)$', VmRenewView.as_view(),
        name='dashboard.views.vm-renew'),

    url(r'^node/list/$', NodeList.as_view(), name='dashboard.views.node-list'),
    url(r'^node/(?P<pk>\d+)/$', NodeDetailView.as_view(),
        name='dashboard.views.node-detail'),
    url(r'^node/(?P<pk>\d+)/add-trait/$', NodeAddTraitView.as_view(),
        name='dashboard.views.node-addtrait'),
    url(r'^tx/(?P<key>.*)/?$', TransferOwnershipConfirmView.as_view(),
        name='dashboard.views.vm-transfer-ownership-confirm'),
    url(r'^node/delete/(?P<pk>\d+)/$', NodeDelete.as_view(),
        name="dashboard.views.delete-node"),
    url(r'^node/status/(?P<pk>\d+)/$', NodeStatus.as_view(),
        name="dashboard.views.status-node"),
    url(r'^node/create/$', NodeCreate.as_view(),
        name='dashboard.views.node-create'),

    url(r'^favourite/$', FavouriteView.as_view(),
        name='dashboard.views.favourite'),
    url(r'^group/delete/(?P<pk>\d+)/$', GroupDelete.as_view(),
        name="dashboard.views.delete-group"),
    url(r'^group/list/$', GroupList.as_view(),
        name='dashboard.views.group-list'),
    url((r'^vm/(?P<pk>\d+)/graph/(?P<metric>cpu|memory|network)/'
         r'(?P<time>[0-9]{1,2}[hdwy])$'),
        VmGraphView.as_view(),
        name='dashboard.views.vm-graph'),
    url((r'^node/(?P<pk>\d+)/graph/(?P<metric>cpu|memory|network)/'
         r'(?P<time>[0-9]{1,2}[hdwy])$'),
        NodeGraphView.as_view(),
        name='dashboard.views.node-graph'),
    url(r'^group/(?P<pk>\d+)/$', GroupDetailView.as_view(),
        name='dashboard.views.group-detail'),
    url(r'^group/(?P<pk>\d+)/acl/$', GroupAclUpdateView.as_view(),
        name='dashboard.views.group-acl'),
    url(r'^groupuser/delete/(?P<pk>\d+)/$', GroupUserDelete.as_view(),
        name="dashboard.views.delete-groupuser"),

    url(r'^notifications/$', NotificationView.as_view(),
        name="dashboard.views.notifications"),

    url(r'^disk/add/$', DiskAddView.as_view(),
        name="dashboard.views.disk-add"),
    url(r'^profile/$', MyPreferencesView.as_view(),
        name="dashboard.views.profile"),
    url(r'^disk/(?P<pk>\d+)/remove/$', DiskRemoveView.as_view(),
        name="dashboard.views.disk-remove"),
)
