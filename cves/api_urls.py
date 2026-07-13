from rest_framework.routers import DefaultRouter

from .api_views import CVEViewSet

router = DefaultRouter()
router.register("cves", CVEViewSet, basename="cve")

urlpatterns = router.urls
