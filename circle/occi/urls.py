from django.conf.urls import url
from views import (OcciLoginView, OcciLogoutView, OcciQueryInterfaceView,
                   OcciComputeView, OcciComputeCollectionView)


urlpatterns = [
    url(r'^login/$', OcciLoginView.as_view()),
    url(r'^logout/$', OcciLogoutView.as_view()),
    url(r'^-/$', OcciQueryInterfaceView.as_view()),
    url(r'^compute/$', OcciComputeCollectionView.as_view()),
    url(r'^compute/(?P<id>\d+)/$', OcciComputeView.as_view()),
]
