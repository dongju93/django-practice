from django.urls import path

from . import views

app_name = "hosts"

urlpatterns = [
    path("", views.HostIPListView.as_view(), name="index"),
    path("data/", views.HostIPDataView.as_view(), name="data"),
    path("create/", views.HostIPCreateView.as_view(), name="create"),
    path("<int:pk>/", views.HostIPDetailView.as_view(), name="detail"),
    path("<int:pk>/update/", views.HostIPUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", views.HostIPDeleteView.as_view(), name="delete"),
]
