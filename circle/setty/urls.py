from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^create/$',
        views.IndexView.as_view(),
        name='setty.views.service-create'),
    url(r'^delete/(?P<pk>\d+)$',
        views.DeleteView.as_view(),
        name='setty.views.service-delete'),
    url(r'^start/(?P<pk>\d+)$',
        views.StartView.as_view(),
        name='setty.views.service-start'),
    url(r'^list/$',
        views.ListView.as_view(),
        name='setty.views.service-list'),
    url(r'^(?P<pk>\d+)/$',
        views.DetailView.as_view(),
        name='setty.views.service-detail'),
]
