from django.conf.urls import patterns, url

from vm.models import Instance

from .views import IndexView, VmDetailView, VmList, AclUpdateView

urlpatterns = patterns(
    '',
    url(r'^$', IndexView.as_view()),
    url(r'^vm/(?P<pk>\d+)/$', VmDetailView.as_view(),
        name='dashboard.views.detail'),
    url(r'^vm/(?P<pk>\d+)/acl/$', AclUpdateView.as_view(model=Instance),
        name='dashboard.views.vm-acl'),
    url(r'^vm/list/$', VmList.as_view(), name='dashboard.views.vm-list'),
)
