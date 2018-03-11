from __future__ import absolute_import, division, print_function, unicode_literals

from rest_framework import serializers

from demos_voting.base.fields import ContentFileField
from demos_voting.base.serializers import (
    CreateBallotListMixin, CreateBallotMixin, CreateElectionMixin, DynamicFieldsMixin,
)
from demos_voting.vote_collector.models import (
    Administrator, Ballot, BallotOption, BallotPart, BallotQuestion, Election, ElectionOption, ElectionQuestion,
)


# Detail serializers ##########################################################

class ElectionSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Election
        exclude = ['id', 'created_at', 'updated_at', 'voting_started_at', 'voting_ended_at']


# Creation serializers ########################################################

class CreateAdministratorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Administrator
        exclude = ['id', 'election', 'user']


class CreateElectionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElectionOption
        exclude = ['id', 'question']


class CreateElectionQuestionSerializer(serializers.ModelSerializer):
    options = CreateElectionOptionSerializer(many=True, allow_empty=False)

    class Meta:
        model = ElectionQuestion
        exclude = ['id', 'election']


class CreateElectionSerializer(CreateElectionMixin, serializers.ModelSerializer):
    questions = CreateElectionQuestionSerializer(many=True, allow_empty=False)
    administrators = CreateAdministratorSerializer(many=True, allow_empty=False, write_only=True)
    certificate_file = ContentFileField(allow_null=True)

    class Meta:
        model = Election
        exclude = ['id', 'state', 'created_at', 'updated_at', 'voting_started_at', 'voting_ended_at']


class CreateBallotOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BallotOption
        exclude = ['id', 'question', 'is_voted']


class CreateBallotQuestionSerializer(serializers.ModelSerializer):
    options = CreateBallotOptionSerializer(many=True, allow_empty=False)

    class Meta:
        model = BallotQuestion
        exclude = ['id', 'part', 'election_question']


class CreateBallotPartSerializer(serializers.ModelSerializer):
    questions = CreateBallotQuestionSerializer(many=True, allow_empty=False)

    class Meta:
        model = BallotPart
        exclude = ['id', 'ballot', 'credential']


class CreateBallotListSerializer(CreateBallotListMixin, serializers.ListSerializer):
    pass


class CreateBallotSerializer(CreateBallotMixin, serializers.ModelSerializer):
    parts = CreateBallotPartSerializer(many=True, allow_empty=False)

    def __init__(self, *args, **kwargs):
        super(CreateBallotSerializer, self).__init__(*args, **kwargs)
        election = self.context['election']
        if election.vote_code_type == election.VOTE_CODE_TYPE_LONG:
            # Remove the vote-code field from the option serializer.
            del self.fields['parts'].child.fields['questions'].child.fields['options'].child.fields['vote_code']

    class Meta:
        model = Ballot
        exclude = ['id', 'election']
        list_serializer_class = CreateBallotListSerializer


# Update serializers ##########################################################

class UpdateElectionSerializer(serializers.ModelSerializer):
    def __new__(cls, *args, **kwargs):
        election = kwargs.get('instance', next(iter(args), None))
        if election.state == election.STATE_SETUP:
            serializer_class = SetupUpdateElectionSerializer
        elif election.state == election.STATE_BALLOT_DISTRIBUTION:
            serializer_class = BallotDistributionUpdateElectionSerializer
        return serializer_class(*args, **kwargs)


class SetupUpdateElectionSerializer(serializers.ModelSerializer):
    state = serializers.ChoiceField([Election.STATE_COMPLETED, Election.STATE_FAILED, Election.STATE_CANCELLED])

    class Meta:
        model = Election
        fields = ['state']

    def validate_state(self, state):
        election = self.instance
        if state == election.STATE_COMPLETED:
            state = election.STATE_BALLOT_DISTRIBUTION
        return state


class BallotDistributionUpdateElectionSerializer(serializers.ModelSerializer):
    state = serializers.ChoiceField([Election.STATE_COMPLETED, Election.STATE_FAILED, Election.STATE_CANCELLED])

    class Meta:
        model = Election
        fields = ['state']

    def validate_state(self, state):
        election = self.instance
        if state == election.STATE_COMPLETED:
            state = election.STATE_VOTING
        return state


# Bulletin Board serializers ##################################################

class BulletinBoardBallotOptionListSerializer(serializers.ListSerializer):
    def to_representation(self, options):
        assert isinstance(options, type(BallotOption.objects))
        # Select only the ballot options that have been marked as voted.
        options = options.filter(is_voted=True).only(*self.child.fields.keys())
        return super(BulletinBoardBallotOptionListSerializer, self).to_representation(options)


class BulletinBoardBallotOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BallotOption
        fields = ['index', 'vote_code']
        list_serializer_class = BulletinBoardBallotOptionListSerializer


class BulletinBoardBallotQuestionSerializer(serializers.ModelSerializer):
    options = BulletinBoardBallotOptionSerializer(many=True, allow_empty=False)

    class Meta:
        model = BallotQuestion
        fields = ['options']


class BulletinBoardBallotPartListSerializer(serializers.ListSerializer):
    def to_representation(self, parts):
        assert isinstance(parts, type(BallotPart.objects))
        # Select only the ballot part that has been cast.
        parts = parts.filter(is_cast=True).prefetch_related('questions')
        return super(BulletinBoardBallotPartListSerializer, self).to_representation(parts)


class BulletinBoardBallotPartSerializer(serializers.ModelSerializer):
    questions = BulletinBoardBallotQuestionSerializer(many=True, allow_empty=False)

    class Meta:
        model = BallotPart
        fields = ['questions', 'tag', 'credential']
        list_serializer_class = BulletinBoardBallotPartListSerializer


class BulletinBoardBallotSerializer(serializers.ModelSerializer):
    parts = BulletinBoardBallotPartSerializer(many=True, allow_empty=False)

    def __init__(self, *args, **kwargs):
        super(BulletinBoardBallotSerializer, self).__init__(*args, **kwargs)
        election = self.context['election']
        if election.vote_code_type == election.VOTE_CODE_TYPE_SHORT:
            # Remove the `vote_code` field from the option serializer.
            del self.fields['parts'].child.fields['questions'].child.fields['options'].child.fields['vote_code']
        elif election.vote_code_type == election.VOTE_CODE_TYPE_LONG:
            # Remove the `credential` field from the part serializer.
            del self.fields['parts'].child.fields['credential']

    class Meta:
        model = Ballot
        fields = ['parts']
