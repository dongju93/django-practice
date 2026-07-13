from django.urls import include, path

urlpatterns = [
    path("", include("snippets.urls")),
    path("", include("cves.api_urls")),
]
