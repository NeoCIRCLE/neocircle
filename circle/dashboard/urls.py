from django.conf.urls import patterns, url

from .views import IndexView, VmDetailView

urlpatterns = patterns('',
                       url(r'^$', IndexView.as_view()),
                       url(r'^vm/(?P<id>\d+)/$', VmDetailView.as_view(),
                           name='dashboard.views.detail'),
)
