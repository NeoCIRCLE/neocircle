from django.conf.urls import url
from views import OcciLoginView, OcciLogoutView, TestView


urlpatterns = [
    url(r'^login/$', OcciLoginView.as_view()),
    url(r'^logout/$', OcciLogoutView.as_view()),
    url(r'^test/$', TestView.as_view()),
]
