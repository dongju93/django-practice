from django.urls import path

from . import views

app_name = "polls"  # pylint: disable=invalid-name
"""
patterns has changed from <question_id> to <pk> (15, 17 line)
This is necessary because we’ll use the `DetailView` generic view to replace our `detail()` and `results()` views
expects the primary key value captured from the URL to be called "pk".
"""
urlpatterns = [  # URL patterns for the 'polls' resource
    # ex: /polls/
    path("", views.IndexView.as_view(), name="index"),
    # ex: /polls/5/
    path("<int:pk>/", views.DetailView.as_view(), name="detail"),
    # ex: /polls/5/results/
    path("<int:pk>/results/", views.ResultsView.as_view(), name="results"),
    # ex: /polls/5/vote/
    path("<int:question_id>/vote/", views.vote, name="vote"),
]
