import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from polls.models import Choice, Question


def create_question(question_text, days):
    """Create a question offset from now by ``days`` (negative = already published)."""
    pub_date = timezone.now() + datetime.timedelta(days=days)
    return Question.objects.create(question_text=question_text, pub_date=pub_date)


class QuestionModelTests(TestCase):
    """`was_published_recently()` is bounded on both sides.

    Without the upper bound a question scheduled far in the future also
    satisfies `now - 1 day <= pub_date` and is reported as "recent", which is
    how the admin list ends up advertising unpublished questions.
    """

    def test_future_question_is_not_recent(self):
        question = Question(pub_date=timezone.now() + datetime.timedelta(days=30))

        self.assertIs(question.was_published_recently(), False)

    def test_old_question_is_not_recent(self):
        question = Question(
            pub_date=timezone.now() - datetime.timedelta(days=1, seconds=1)
        )

        self.assertIs(question.was_published_recently(), False)

    def test_question_published_within_last_day_is_recent(self):
        question = Question(
            pub_date=timezone.now() - datetime.timedelta(hours=23, minutes=59)
        )

        self.assertIs(question.was_published_recently(), True)


class QuestionQuerySetTests(TestCase):
    def test_published_excludes_future_questions(self):
        past = create_question("Past question", days=-1)
        create_question("Future question", days=1)

        self.assertQuerySetEqual(Question.objects.published(), [past])

    def test_default_manager_still_returns_future_questions(self):
        # `objects` stays unfiltered on purpose so the admin can schedule and
        # edit questions before their publication date.
        create_question("Future question", days=1)

        self.assertEqual(Question.objects.count(), 1)


class QuestionIndexViewTests(TestCase):
    """P2-1 regression: the list must not leak questions before `pub_date`."""

    def test_no_questions_shows_placeholder(self):
        response = self.client.get(reverse("polls:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No polls are available.")
        self.assertQuerySetEqual(response.context["latest_question_list"], [])

    def test_past_question_is_listed(self):
        question = create_question("Past question", days=-1)

        response = self.client.get(reverse("polls:index"))

        self.assertQuerySetEqual(response.context["latest_question_list"], [question])

    def test_future_question_is_not_listed(self):
        create_question("Future question", days=1)

        response = self.client.get(reverse("polls:index"))

        self.assertContains(response, "No polls are available.")
        self.assertNotContains(response, "Future question")
        self.assertQuerySetEqual(response.context["latest_question_list"], [])

    def test_only_past_questions_are_listed_when_both_exist(self):
        past = create_question("Past question", days=-1)
        create_question("Future question", days=1)

        response = self.client.get(reverse("polls:index"))

        self.assertQuerySetEqual(response.context["latest_question_list"], [past])

    def test_list_is_limited_to_five_most_recent_questions(self):
        questions = [
            create_question(f"Question {index}", days=-index) for index in range(1, 7)
        ]

        response = self.client.get(reverse("polls:index"))

        self.assertQuerySetEqual(
            response.context["latest_question_list"], questions[:5]
        )


class QuestionDetailViewTests(TestCase):
    def test_future_question_returns_404(self):
        question = create_question("Future question", days=1)

        response = self.client.get(reverse("polls:detail", args=(question.id,)))

        self.assertEqual(response.status_code, 404)

    def test_past_question_is_displayed(self):
        question = create_question("Past question", days=-1)

        response = self.client.get(reverse("polls:detail", args=(question.id,)))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, question.question_text)


class QuestionResultsViewTests(TestCase):
    def test_future_question_results_return_404(self):
        # Results are a second read path to the same row; gating only the
        # detail view would still expose the question text and vote counts.
        question = create_question("Future question", days=1)

        response = self.client.get(reverse("polls:results", args=(question.id,)))

        self.assertEqual(response.status_code, 404)

    def test_past_question_results_are_displayed(self):
        question = create_question("Past question", days=-1)
        question.choice_set.create(choice_text="Yes", votes=3)

        response = self.client.get(reverse("polls:results", args=(question.id,)))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Yes")
        self.assertContains(response, "3 votes")


class VoteViewTests(TestCase):
    def test_voting_on_a_future_question_returns_404_without_counting(self):
        question = create_question("Future question", days=1)
        choice = question.choice_set.create(choice_text="Yes")

        response = self.client.post(
            reverse("polls:vote", args=(question.id,)), {"choice": choice.id}
        )

        self.assertEqual(response.status_code, 404)
        choice.refresh_from_db()
        self.assertEqual(choice.votes, 0)

    def test_voting_on_a_past_question_increments_and_redirects(self):
        question = create_question("Past question", days=-1)
        choice = question.choice_set.create(choice_text="Yes")

        response = self.client.post(
            reverse("polls:vote", args=(question.id,)), {"choice": choice.id}
        )

        self.assertRedirects(response, reverse("polls:results", args=(question.id,)))
        choice.refresh_from_db()
        self.assertEqual(choice.votes, 1)

    def test_missing_choice_redisplays_the_form_with_an_error(self):
        question = create_question("Past question", days=-1)
        question.choice_set.create(choice_text="Yes")

        response = self.client.post(reverse("polls:vote", args=(question.id,)), {})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You didn&#x27;t select a choice.")

    def test_choice_from_another_question_is_rejected(self):
        question = create_question("Past question", days=-1)
        other_choice = create_question("Other question", days=-1).choice_set.create(
            choice_text="Elsewhere"
        )

        response = self.client.post(
            reverse("polls:vote", args=(question.id,)), {"choice": other_choice.id}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You didn&#x27;t select a choice.")
        other_choice.refresh_from_db()
        self.assertEqual(other_choice.votes, 0)
        self.assertEqual(Choice.objects.filter(votes__gt=0).count(), 0)
