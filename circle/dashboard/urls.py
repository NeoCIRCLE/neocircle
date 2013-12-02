from django.conf.urls import patterns, url

from vm.models import Instance
from .views import (
    IndexView, VmDetailView, VmList, VmCreate, TemplateDetail, AclUpdateView,
    VmDelete, VmMassDelete, vm_activity, NodeList, NodeDetailView,
    TransferOwnershipView, TransferOwnershipConfirmView
)

urlpatterns = patterns(
    '',
    url(r'^$', IndexView.as_view(), name="dashboard.index"),
    url(r'^template/(?P<pk>\d+)/$', TemplateDetail.as_view(),
        name='dashboard.views.template-detail'),
    url(r'^vm/(?P<pk>\d+)/$', VmDetailView.as_view(),
        name='dashboard.views.detail'),
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
    url(r'^node/list/$', NodeList.as_view(), name='dashboard.views.node-list'),
    url(r'^node/(?P<pk>\d+)/$', NodeDetailView.as_view(),
        name='dashboard.views.node-detail'),
    url(r'^tx/$', TransferOwnershipConfirmView.as_view(),
        name='dashboard.views.vm-transfer-ownership-confirm'),

)
