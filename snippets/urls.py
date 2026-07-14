from rest_framework.routers import SimpleRouter

from snippets.views import SnippetViewSet

router = SimpleRouter()
router.register("snippets", SnippetViewSet)

urlpatterns = router.urls
