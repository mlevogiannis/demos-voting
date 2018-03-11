from __future__ import absolute_import, division, print_function, unicode_literals

from django.db import models


class BallotQuestionManager(models.Manager):
    def get_queryset(self):
        queryset = super(BallotQuestionManager, self).get_queryset()
        queryset = queryset.annotate(_election_question_index=models.F('election_question__index'))
        return queryset


class BallotOptionManager(models.Manager):
    def get_queryset(self):
        queryset = super(BallotOptionManager, self).get_queryset()
        queryset = queryset.annotate(_election_option_index=models.F('election_option__index'))
        return queryset
