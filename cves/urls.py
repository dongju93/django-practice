from django.urls import path

from . import views

app_name = "cves"

urlpatterns = [
    path("", views.CVEListView.as_view(), name="list"),
    path("create/", views.CVECreateView.as_view(), name="create"),
    path("<str:cve_id>/", views.CVEDetailView.as_view(), name="detail"),
    path("<str:cve_id>/edit/", views.CVEUpdateView.as_view(), name="edit"),
    path("<str:cve_id>/delete/", views.CVEDeleteView.as_view(), name="delete"),
]
