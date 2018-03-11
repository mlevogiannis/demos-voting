from __future__ import absolute_import, division, print_function, unicode_literals

from rest_framework import serializers

from demos_voting.ballot_distributor.models import (
    Administrator, Ballot, BallotOption, BallotPart, BallotQuestion, Election, ElectionOption, ElectionQuestion, Voter,
)
from demos_voting.base.fields import ContentFileField
from demos_voting.base.serializers import (
    CreateBallotListMixin, CreateBallotMixin, CreateElectionMixin, DynamicFieldsMixin,
)


# Detail serializers ##########################################################

class ElectionSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Election
        exclude = ['id', 'created_at', 'updated_at', 'ballot_distribution_started_at', 'ballot_distribution_ended_at']


class VoterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Voter
        exclude = ['id', 'election', 'user']
        extra_kwargs = {'email': {'source': 'get_email'}}


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
    administrators = CreateAdministratorSerializer(many=True, allow_empty=False, write_only=True)
    questions = CreateElectionQuestionSerializer(many=True, allow_empty=False)
    certificate_file = ContentFileField(allow_null=True)

    class Meta:
        model = Election
        exclude = [
            'id', 'state', 'created_at', 'updated_at', 'ballot_distribution_started_at', 'ballot_distribution_ended_at'
        ]


class CreateBallotOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BallotOption
        exclude = ['id', 'question']


class CreateQuestionSetupSerializer(serializers.ModelSerializer):
    options = CreateBallotOptionSerializer(many=True, allow_empty=False)

    class Meta:
        model = BallotQuestion
        exclude = ['id', 'part', 'election_question']


class CreateBallotPartSerializer(serializers.ModelSerializer):
    questions = CreateQuestionSetupSerializer(many=True, allow_empty=False)

    class Meta:
        model = BallotPart
        exclude = ['id', 'ballot']


class CreateBallotListSerializer(CreateBallotListMixin, serializers.ListSerializer):
    pass


class CreateBallotSerializer(CreateBallotMixin, serializers.ModelSerializer):
    parts = CreateBallotPartSerializer(many=True, allow_empty=False)

    class Meta:
        model = Ballot
        exclude = ['id', 'election', 'voter', 'archive', 'file']
        list_serializer_class = CreateBallotListSerializer


# Update serializers ##########################################################

class UpdateElectionSerializer(serializers.ModelSerializer):
    def __new__(cls, *args, **kwargs):
        election = kwargs.get('instance', next(iter(args), None))
        if election.state == election.STATE_SETUP:
            serializer_class = SetupUpdateElectionSerializer
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
