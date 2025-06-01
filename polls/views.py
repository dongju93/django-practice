from django.db.models import F
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import generic

from .models import Choice, Question

"""
Each generic view needs to know what model it will be acting upon
- DetailView generic view uses a template called <app name>/<model name>_detail.html.
- ListView generic view uses a default template called <app name>/<model name>_list.html
"""


class IndexView(generic.ListView):
    """
    ListView, the automatically generated context variable is `question_list`.
    To override this we provide the `context_object_name` attribute,
    specifying that we want to use `latest_question_list` instead.
    """

    template_name = "polls/index.html"
    # context_object_name is used to specify the name of the variable to be used in the template
    context_object_name = "latest_question_list"

    def get_queryset(self):
        """Return the last five published questions."""
        return Question.objects.order_by("-pub_date")[:5]


class DetailView(generic.DetailView):
    """
    For DetailView the `question` variable is provided automatically
    since we’re using a Django model (Question)
    """

    model = Question  # This is the model that the DetailView will use
    template_name = "polls/detail.html"  # The template to render the detail view


class ResultsView(generic.DetailView):
    model = Question  # This is the model that the ResultsView will use
    template_name = "polls/results.html"  # The template to render the results view


def vote(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    try:
        selected_choice = question.choice_set.get(pk=request.POST["choice"])
    except (KeyError, Choice.DoesNotExist):
        # Redisplay the question voting form.
        return render(
            request,
            "polls/detail.html",
            {
                "question": question,
                "error_message": "You didn't select a choice.",
            },
        )
    else:
        selected_choice.votes = F("votes") + 1  #  Increment the votes in database level
        selected_choice.save()  # Save the updated choice with incremented votes
        # Always return an HttpResponseRedirect after successfully dealing
        # with POST data. This prevents data from being posted twice if a
        # user hits the Back button.
        return HttpResponseRedirect(reverse("polls:results", args=(question.id,)))
