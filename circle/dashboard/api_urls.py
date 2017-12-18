from rest_framework import routers
from . import api_views

router = routers.DefaultRouter()
router.register('user', api_views.UserViewSet)

urlpatterns = router.urls
