from django.urls import include, path

urlpatterns = [
    path("", include("snippets.urls")),
    # Add more app URLs here for v1 API:
    # path("polls/", include("polls.urls")),
    # path("users/", include("users.urls")),
]