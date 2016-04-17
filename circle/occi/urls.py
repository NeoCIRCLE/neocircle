from django.conf.urls import url
from views import OcciLoginView, OcciLogoutView, WakeUpVM, SleepVM


urlpatterns = [
    url(r'^login/$', OcciLoginView.as_view()),
    url(r'^logout/$', OcciLogoutView.as_view()),
    url(r'^wakeup/$', WakeUpVM.as_view()),
    url(r'^sleep/$', SleepVM.as_view()),
]
