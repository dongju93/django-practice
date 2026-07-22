import datetime

from django.db import models
from django.utils import timezone


class QuestionQuerySet(models.QuerySet):
    def published(self):
        """Exclude questions scheduled for the future.

        `timezone.now()` is evaluated on every call so a long-lived worker
        process does not keep using the cutoff it had at startup.
        """
        return self.filter(pub_date__lte=timezone.now())


class Question(models.Model):
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField("date published")

    # Adds `.published()` while keeping `objects` itself unfiltered, so the
    # admin can still list and edit questions scheduled for the future.
    objects = QuestionQuerySet.as_manager()

    def __str__(self):  # pylint: disable=invalid-str-returned
        return self.question_text

    def was_published_recently(self):
        """True only for questions published within the last 24 hours.

        The upper bound matters: without it a question dated far in the future
        also satisfies the lower bound and is reported as "recent".
        """
        now = timezone.now()
        return now - datetime.timedelta(days=1) <= self.pub_date <= now


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice_text = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)

    def __str__(self):  # pylint: disable=invalid-str-returned
        return self.choice_text
