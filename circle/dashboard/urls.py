from django.conf.urls import patterns, url

from .views import IndexView, VmDetailView, VmList

urlpatterns = patterns(
    '',
    url(r'^$', IndexView.as_view()),
    url(r'^vm/(?P<pk>\d+)/$', VmDetailView.as_view(),
        name='dashboard.views.detail'),
    url(r'^vm/list/$', VmList.as_view(), name='dashboard.views.vm-list'),
)
