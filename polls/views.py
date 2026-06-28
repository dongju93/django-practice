"""
Each generic view needs to know what model it will be acting upon
- DetailView generic view uses a template called <app name>/<model name>_detail.html.
- ListView generic view uses a default template called <app name>/<model name>_list.html
"""

from django.db.models import F
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import generic

from polls.models import Choice, Question


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
        return Question.objects.order_by("-pub_date")[:5]  # pylint: disable=no-member


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


def datatables(request):
    """
    Render a DataTables-powered table whose cells can be selected by row and
    column, then copied as JSON.

    The table is populated from the related ``Choice`` rows so the demo always
    has multi-column, multi-row data to select from. When the database has no
    choices yet, a small set of sample rows is used instead so the feature can
    still be exercised.
    """

    columns = ["ID", "Question", "Choice", "Votes", "Published"]

    choices = Choice.objects.select_related("question").order_by(
        "question__pub_date", "id"
    )

    rows = [
        [
            choice.id,
            choice.question.question_text,
            choice.choice_text,
            choice.votes,
            choice.question.pub_date.strftime("%Y-%m-%d"),
        ]
        for choice in choices
    ]

    if not rows:
        # Fallback sample data so the page is usable without seeded records.
        rows = [
            [1, "What's your favorite language?", "Python", 42, "2026-01-02"],
            [2, "What's your favorite language?", "Rust", 17, "2026-01-02"],
            [3, "What's your favorite language?", "Go", 23, "2026-01-02"],
            [4, "Best editor?", "VS Code", 55, "2026-02-11"],
            [5, "Best editor?", "Neovim", 31, "2026-02-11"],
            [6, "Best editor?", "JetBrains", 12, "2026-02-11"],
        ]

    return render(
        request,
        "polls/datatables.html",
        {
            "columns": columns,
            "rows": rows,
        },
    )


def vote(request, question_id):
    question = get_object_or_404(
        Question,
        pk=question_id,
    )
    try:
        selected_choice = question.choice_set.get(pk=request.POST["choice"])
    except (
        KeyError,
        Choice.DoesNotExist,
    ):  # pylint: disable=no-member
        # Redisplay the question voting form.
        return render(
            request,
            "polls/detail.html",
            {
                "question": question,
                "error_message": "You didn't select a choice.",
            },
        )
    selected_choice.votes = F("votes") + 1  #  Increment the votes in database level
    selected_choice.save()  # Save the updated choice with incremented votes
    # Always return an HttpResponseRedirect after successfully dealing
    # with POST data. This prevents data from being posted twice if a
    # user hits the Back button.
    return HttpResponseRedirect(
        reverse(
            "polls:results",
            args=(question.id,),
        )
    )
