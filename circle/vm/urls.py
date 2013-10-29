from django.conf.urls import patterns, url

from .views import BootUrl


urlpatterns = patterns(
    '',
    url(r'^b/(?P<token>.*)/$', BootUrl.as_view()),
)
