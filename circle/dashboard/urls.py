from django.conf.urls import patterns, include, url

from .views import IndexView, VmDetailView

urlpatterns = patterns('',
                       url(r'^$', IndexView.as_view()),
                       url(r'^vm/\d+/$', VmDetailView.as_view()),
)
