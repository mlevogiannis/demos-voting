# File: serializers.py

from __future__ import absolute_import, division, print_function, unicode_literals

from rest_framework import serializers

from demos_voting.apps.bds.models import Election, Question, Option, Ballot, Part, PQuestion, POption


class OptionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Option
        fields = ['index', 'name']


class QuestionSerializer(serializers.ModelSerializer):

    options = OptionSerializer(many=True)

    class Meta:
        model = Question
        fields = ['index', 'name', 'min_choices', 'max_choices', 'table_layout', 'options']


class ElectionSerializer(serializers.ModelSerializer):

    questions = QuestionSerializer(many=True)

    class Meta:
        model = Election
        fields = [
            'id', 'name', 'voting_starts_at', 'voting_ends_at', 'state', 'type', 'votecode_type', 'security_code_type',
            'ballot_count', 'credential_length', 'votecode_length', 'receipt_length', 'security_code_length',
            'curve_name', 'questions'
        ]


class POptionSerializer(serializers.ModelSerializer):

    class Meta:
        model = POption
        fields = ['index', 'votecode', 'receipt']


class PQuestionSerializer(serializers.ModelSerializer):

    options = POptionSerializer(many=True)

    class Meta:
        model = PQuestion
        fields = ['options']


class PartSerializer(serializers.ModelSerializer):

    questions = PQuestionSerializer(many=True)

    class Meta:
        model = Part
        fields = ['tag', 'security_code', 'questions']


class BallotSerializer(serializers.ModelSerializer):

    parts = PartSerializer(many=True)

    class Meta:
        model = Ballot
        fields = ['serial_number', 'credential', 'parts']

