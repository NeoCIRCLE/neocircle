from django.conf.urls import url
from views import testView


urlpatterns = [
        url(r'^test$', testView.as_view()),
]
