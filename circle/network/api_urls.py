from rest_framework import routers

from . import api_views


router = routers.DefaultRouter()
router.register('blacklist', api_views.BlacklistViewSet)
router.register('domains', api_views.DomainViewSet)
router.register('firewalls', api_views.FirewallViewSet)
router.register('groups', api_views.GroupViewSet)
router.register('hosts', api_views.HostViewSet)
router.register('records', api_views.RecordViewSet)
router.register('rules', api_views.RuleViewSet)
router.register('switchports', api_views.SwitchPortViewSet)
router.register('vlans', api_views.VlanViewSet)
router.register('vlangroups', api_views.VlanGroupViewSet)


urlpatterns = router.urls
