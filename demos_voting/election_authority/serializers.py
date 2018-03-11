from __future__ import absolute_import, division, print_function, unicode_literals

from cryptography.hazmat.primitives.serialization import Encoding

from rest_framework import serializers

from demos_voting.base.serializers import DynamicFieldsMixin
from demos_voting.election_authority.models import (
    Administrator, Ballot, BallotOption, BallotPart, BallotQuestion, Election, ElectionOption, ElectionQuestion,
    Trustee,
)


# Detail serializers ##########################################################

class AdministratorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Administrator
        exclude = ['id', 'election', 'user']
        extra_kwargs = {'email': {'source': 'get_email'}}


class TrusteeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trustee
        exclude = ['id', 'election', 'user', 'secret_key']
        extra_kwargs = {'email': {'source': 'get_email'}}


class ElectionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElectionOption
        exclude = ['id', 'question']


class ElectionQuestionSerializer(serializers.ModelSerializer):
    options = ElectionOptionSerializer(many=True, allow_empty=False)

    class Meta:
        model = ElectionQuestion
        exclude = ['id', 'election']


class ElectionSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    administrators = AdministratorSerializer(many=True, allow_empty=False)
    questions = ElectionQuestionSerializer(many=True, allow_empty=False)
    certificate_file = serializers.SerializerMethodField()

    class Meta:
        model = Election
        exclude = ['id', 'created_at', 'updated_at', 'setup_started_at', 'setup_ended_at', 'tasks', 'private_key_file']

    def get_certificate_file(self, election):
        if election.vote_code_type == election.VOTE_CODE_TYPE_SHORT:
            return None
        elif election.vote_code_type == election.VOTE_CODE_TYPE_LONG:
            return election.certificate.public_bytes(encoding=Encoding.PEM)


# Ballot Distributor serializers ##############################################

class BallotDistributorBallotOptionListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        ret = super(BallotDistributorBallotOptionListSerializer, self).to_representation(data)
        # Fix the list's order after restoring the options' original indices.
        ret.sort(key=lambda option_data: option_data['index'])
        return ret


class BallotDistributorBallotOptionSerializer(serializers.ModelSerializer):
    index = serializers.SerializerMethodField()

    class Meta:
        model = BallotOption
        fields = ['index', 'vote_code', 'receipt']
        list_serializer_class = BallotDistributorBallotOptionListSerializer

    def get_index(self, ballot_option):
        # Restore the option's original index.
        ballot_question = ballot_option.question
        return ballot_question.permutation[ballot_option.index]


class BallotDistributorBallotQuestionSerializer(serializers.ModelSerializer):
    options = BallotDistributorBallotOptionSerializer(many=True, allow_empty=False)

    class Meta:
        model = BallotQuestion
        fields = ['options']


class BallotDistributorBallotPartSerializer(serializers.ModelSerializer):
    questions = BallotDistributorBallotQuestionSerializer(many=True, allow_empty=False)

    class Meta:
        model = BallotPart
        fields = ['questions', 'tag', 'credential', 'security_code']


class BallotDistributorBallotSerializer(serializers.ModelSerializer):
    parts = BallotDistributorBallotPartSerializer(many=True, allow_empty=False)

    class Meta:
        model = Ballot
        fields = ['serial_number', 'parts']


# Bulletin Board serializers  #################################################

class BulletinBoardBallotOptionSerializer(serializers.ModelSerializer):
    vote_code = serializers.SerializerMethodField()
    commitment = serializers.JSONField()
    zk1 = serializers.JSONField()

    class Meta:
        model = BallotOption
        fields = ['index', 'vote_code', 'vote_code_hash', 'receipt', 'commitment', 'zk1']

    def get_vote_code(self, ballot_option):
        election = ballot_option.election
        if election.vote_code_type == election.VOTE_CODE_TYPE_SHORT:
            return ballot_option.vote_code
        elif election.vote_code_type == election.VOTE_CODE_TYPE_LONG:
            return None


class BulletinBoardBallotQuestionSerializer(serializers.ModelSerializer):
    options = BulletinBoardBallotOptionSerializer(many=True, allow_empty=False)
    zk1 = serializers.JSONField()

    class Meta:
        model = BallotQuestion
        fields = ['options', 'zk1']


class BulletinBoardBallotPartSerializer(serializers.ModelSerializer):
    questions = BulletinBoardBallotQuestionSerializer(many=True, allow_empty=False)

    class Meta:
        model = BallotPart
        fields = ['questions', 'tag', 'credential_hash']


class BulletinBoardBallotSerializer(serializers.ModelSerializer):
    parts = BulletinBoardBallotPartSerializer(many=True, allow_empty=False)

    class Meta:
        model = Ballot
        fields = ['serial_number', 'parts']


# Vote Collector serializers ##################################################

class VoteCollectorBallotOptionSerializer(serializers.ModelSerializer):
    vote_code = serializers.SerializerMethodField()

    class Meta:
        model = BallotOption
        fields = ['index', 'vote_code', 'vote_code_hash', 'receipt']

    def get_vote_code(self, ballot_option):
        election = ballot_option.election
        if election.vote_code_type == election.VOTE_CODE_TYPE_SHORT:
            return ballot_option.vote_code
        elif election.vote_code_type == election.VOTE_CODE_TYPE_LONG:
            return None


class VoteCollectorBallotQuestionSerializer(serializers.ModelSerializer):
    options = VoteCollectorBallotOptionSerializer(many=True, allow_empty=False)

    class Meta:
        model = BallotQuestion
        fields = ['options']


class VoteCollectorBallotPartSerializer(serializers.ModelSerializer):
    questions = VoteCollectorBallotQuestionSerializer(many=True, allow_empty=False)

    class Meta:
        model = BallotPart
        fields = ['questions', 'tag', 'credential_hash']


class VoteCollectorBallotSerializer(serializers.ModelSerializer):
    parts = VoteCollectorBallotPartSerializer(many=True, allow_empty=False)

    class Meta:
        model = Ballot
        fields = ['serial_number', 'parts']
