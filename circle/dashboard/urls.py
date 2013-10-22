from django.conf.urls import patterns, url

from .views import IndexView, VmDetailView, VmList, VmCreate, TemplateDetail

urlpatterns = patterns(
    '',
    url(r'^$', IndexView.as_view()),
    url(r'^template/(?P<pk>\d+)/$', TemplateDetail.as_view(),
        name='dashboard.views.template-detail'),
    url(r'^vm/(?P<pk>\d+)/$', VmDetailView.as_view(),
        name='dashboard.views.detail'),
    url(r'^vm/list/$', VmList.as_view(), name='dashboard.views.vm-list'),
    url(r'^vm/create/$', VmCreate.as_view(),
        name='dashboard.views.vm-create'),
)
