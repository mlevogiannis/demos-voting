from __future__ import absolute_import, division, print_function, unicode_literals

import base64
import binascii
import re

from django.core.validators import MaxLengthValidator
from django.db import transaction

from rest_framework import serializers
from rest_framework.reverse import reverse
from rest_framework.settings import api_settings
from rest_framework_nested import serializers as nested_serializers

import six

from demos_voting.base.fields import ContentFileField
from demos_voting.base.serializers import (
    CreateBallotListMixin, CreateBallotMixin, CreateElectionMixin, DynamicFieldsMixin,
)
from demos_voting.base.utils import base32, hasher
from demos_voting.bulletin_board.models import (
    Administrator, Ballot, BallotOption, BallotPart, BallotQuestion, Election, ElectionOption, ElectionQuestion,
    Trustee, Voter,
)
from demos_voting.bulletin_board.tasks import generate_election_results


# Detail serializers ##########################################################

class ElectionOptionSerializer(serializers.ModelSerializer):
    is_blank = serializers.BooleanField()

    class Meta:
        model = ElectionOption
        exclude = ['id', 'question']

    def to_representation(self, election_option):
        data = super(ElectionOptionSerializer, self).to_representation(election_option)
        election = election_option.election
        if election.state == election.STATE_TALLY:
            if 'vote_count' in data:
                data['vote_count'] = None
        return data


class ElectionQuestionSerializer(serializers.ModelSerializer):
    options = ElectionOptionSerializer(many=True, allow_empty=False)
    option_count = serializers.IntegerField()
    blank_option_count = serializers.IntegerField()
    tally_commitment = serializers.JSONField()
    tally_decommitment = serializers.JSONField()

    class Meta:
        model = ElectionQuestion
        exclude = ['id', 'election', 'option_table_layout']

    def to_representation(self, election_question):
        data = super(ElectionQuestionSerializer, self).to_representation(election_question)
        election = election_question.election
        if election.state == election.STATE_TALLY:
            if 'tally_decommitment' in data:
                data['tally_decommitment'] = None
        return data


class ElectionSerializer(DynamicFieldsMixin, serializers.HyperlinkedModelSerializer):
    ballots_url = serializers.HyperlinkedIdentityField(
        view_name='bulletin-board:api:ballot-list',
        lookup_field='slug',
        lookup_url_kwarg='election_slug',
    )
    questions = ElectionQuestionSerializer(many=True, allow_empty=False)
    question_count = serializers.IntegerField()
    certificate_url = serializers.SerializerMethodField()

    class Meta:
        model = Election
        exclude = ['created_at', 'updated_at', 'tally_started_at', 'tally_ended_at', 'certificate_file']
        extra_kwargs = {
            'url': {
                'view_name': 'bulletin-board:api:election-detail',
                'lookup_field': 'slug',
            },
        }

    def get_certificate_url(self, obj):
        if obj.certificate_file:
            return reverse(
                viewname='bulletin-board:media:election-certificate',
                kwargs={'slug': obj.slug},
                request=self.context['request'],
            )


class BallotOptionSerializer(serializers.ModelSerializer):
    commitment = serializers.JSONField()
    decommitment = serializers.JSONField(allow_null=True)
    zk1 = serializers.JSONField()
    zk2 = serializers.JSONField(allow_null=True)
    original_index = serializers.IntegerField(allow_null=True, source='_election_option_index')

    class Meta:
        model = BallotOption
        exclude = ['id', 'question']

    def to_representation(self, ballot_option):
        data = super(BallotOptionSerializer, self).to_representation(ballot_option)
        election = ballot_option.election
        if election.state == election.STATE_VOTING:
            if 'is_voted' in data:
                data['is_voted'] = None
            if election.vote_code_type == election.VOTE_CODE_TYPE_LONG and 'vote_code' in data:
                data['vote_code'] = None
        elif election.state == election.STATE_TALLY:
            if 'decommitment' in data:
                data['decommitment'] = None
            if 'zk2' in data:
                data['zk2'] = None
            if 'original_index' in data:
                data['original_index'] = None
        return data


class BallotQuestionSerializer(serializers.ModelSerializer):
    options = BallotOptionSerializer(many=True, allow_empty=False)
    index = serializers.IntegerField(source='_election_question_index')
    zk1 = serializers.JSONField()
    zk2 = serializers.JSONField(allow_null=True)

    class Meta:
        model = BallotQuestion
        exclude = ['id', 'part', 'election_question']

    def to_representation(self, ballot_question):
        data = super(BallotQuestionSerializer, self).to_representation(ballot_question)
        election = ballot_question.election
        if election.state == election.STATE_TALLY:
            if 'zk2' in data:
                data['zk2'] = None
        return data


class BallotPartSerializer(serializers.ModelSerializer):
    questions = BallotQuestionSerializer(many=True, allow_empty=False)
    is_cast = serializers.BooleanField()

    class Meta:
        model = BallotPart
        exclude = ['id', 'ballot']

    def to_representation(self, ballot_option):
        data = super(BallotPartSerializer, self).to_representation(ballot_option)
        election = ballot_option.election
        if election.state == election.STATE_VOTING:
            if election.vote_code_type == election.VOTE_CODE_TYPE_SHORT and 'credential' in data:
                data['credential'] = None
            if 'is_cast' in data:
                data['is_cast'] = None
        return data


class BallotSerializer(DynamicFieldsMixin, nested_serializers.NestedHyperlinkedModelSerializer):
    election_url = serializers.HyperlinkedRelatedField(
        view_name='bulletin-board:api:election-detail',
        lookup_field='slug',
        source='election',
        read_only=True,
    )
    parts = BallotPartSerializer(many=True, allow_empty=False)

    class Meta:
        model = Ballot
        exclude = ['election']
        extra_kwargs = {
            'url': {
                'view_name': 'bulletin-board:api:ballot-detail',
                'lookup_field': 'serial_number',
                'parent_lookup_kwargs': {
                    'election_slug': 'election__slug',
                },
            },
        }


# Creation serializers ########################################################

class CreateAdministratorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Administrator
        exclude = ['id', 'election', 'user']


class CreateElectionOptionSetupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElectionOption
        exclude = ['id', 'question', 'vote_count']


class CreateElectionQuestionSerializer(serializers.ModelSerializer):
    options = CreateElectionOptionSetupSerializer(many=True, allow_empty=False)

    class Meta:
        model = ElectionQuestion
        exclude = ['id', 'election']


class CreateElectionSerializer(CreateElectionMixin, serializers.ModelSerializer):
    administrators = CreateAdministratorSerializer(many=True, allow_empty=False)
    questions = CreateElectionQuestionSerializer(many=True, allow_empty=False)
    certificate_file = ContentFileField(allow_null=True)

    class Meta:
        model = Election
        exclude = ['id', 'state', 'created_at', 'updated_at', 'tally_started_at', 'tally_ended_at', 'coins']


class CreateBallotOptionSerializer(serializers.ModelSerializer):
    commitment = serializers.JSONField()
    zk1 = serializers.JSONField()

    class Meta:
        model = BallotOption
        exclude = ['id', 'question', 'is_voted']


class CreateBallotQuestionSerializer(serializers.ModelSerializer):
    options = CreateBallotOptionSerializer(many=True, allow_empty=False)
    zk1 = serializers.JSONField()

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


class CreateTrusteeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trustee
        exclude = ['id', 'election', 'user']

    def create(self, validated_data):
        validated_data['election_id'] = self.context['election'].pk
        return super(CreateTrusteeSerializer, self).create(validated_data)


class CreateVoterListSerializer(serializers.ListSerializer):
    default_error_messages = {
        'max_length': "This value's length must be at most %(limit_value)s.",
    }

    def __init__(self, *args, **kwargs):
        super(CreateVoterListSerializer, self).__init__(*args, **kwargs)
        election = self.context['election']
        remaining_voters = election.ballot_count - election.voters.count()
        self.validators.append(MaxLengthValidator(remaining_voters, message=self.error_messages['max_length']))


class CreateVoterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Voter
        exclude = ['id', 'election', 'user']
        list_serializer_class = CreateVoterListSerializer

    def create(self, validated_data):
        validated_data['election_id'] = self.context['election'].pk
        return super(CreateVoterSerializer, self).create(validated_data)


# Update serializers ##########################################################

class UpdateElectionSerializer(serializers.ModelSerializer):
    def __new__(cls, *args, **kwargs):
        election = kwargs.get('instance', next(iter(args), None))
        if election.state == election.STATE_SETUP:
            serializer_class = SetupUpdateElectionSerializer
        elif election.state == election.STATE_BALLOT_DISTRIBUTION:
            serializer_class = BallotDistributionUpdateElectionSerializer
        elif election.state == election.STATE_VOTING:
            serializer_class = VotingUpdateElectionSerializer
        elif election.state == election.STATE_TALLY:
            serializer_class = TallyUpdateElectionSerializer
        return serializer_class(*args, **kwargs)


class UpdateBallotSerializer(serializers.Serializer):
    def __new__(cls, *args, **kwargs):
        election = kwargs['context']['election']
        if election.state == election.STATE_VOTING:
            serializer_class = VotingUpdateBallotSerializer
        elif election.state == election.STATE_TALLY:
            serializer_class = TallyUpdateBallotSerializer
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


class VotingUpdateElectionSerializer(serializers.ModelSerializer):
    state = serializers.ChoiceField([Election.STATE_COMPLETED, Election.STATE_FAILED, Election.STATE_CANCELLED])

    class Meta:
        model = Election
        fields = ['state', 'voting_ends_at']

    def validate_state(self, state):
        election = self.instance
        if state == election.STATE_COMPLETED:
            state = election.STATE_TALLY
        return state

    def validate_voting_ends_at(self, voting_ends_at):
        election = self.instance
        if voting_ends_at <= election.voting_ends_at:
            raise serializers.ValidationError("The voting end time can only be extended.")
        return voting_ends_at


class VotingUpdateBallotOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BallotOption
        fields = ['index', 'vote_code']
        extra_kwargs = {
            'vote_code': {'required': True},
        }


class VotingUpdateBallotQuestionSerializer(serializers.ModelSerializer):
    options = VotingUpdateBallotOptionSerializer(many=True, allow_empty=True)

    class Meta:
        model = BallotQuestion
        fields = ['options']


class VotingUpdateBallotPartSerializer(serializers.ModelSerializer):
    questions = VotingUpdateBallotQuestionSerializer(many=True, allow_empty=False)

    class Meta:
        model = BallotPart
        fields = ['questions', 'tag', 'credential']
        extra_kwargs = {
            'credential': {'required': True},
        }


class VotingUpdateBallotSerializer(serializers.ModelSerializer):
    default_error_messages = {
        'min_length': "This value's length must be at least %(limit_value)d.",
        'max_length': "This value's length must be at most %(limit_value)d.",
        'exact_length': "This value's length must be exactly %(limit_value)d.",
    }

    parts = VotingUpdateBallotPartSerializer(many=True, allow_empty=False)

    def __init__(self, *args, **kwargs):
        kwargs['partial'] = False  # all fields are always required
        super(VotingUpdateBallotSerializer, self).__init__(*args, **kwargs)
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

    def validate(self, data):
        data = super(VotingUpdateBallotSerializer, self).validate(data)
        election = self.context['election']
        ballot = self.instance
        # Check if this ballot has already been updated.
        if ballot.parts.filter(is_cast=True).exists():
            e = "This ballot has already been updated."
            raise serializers.ValidationError({api_settings.NON_FIELD_ERRORS_KEY: e})
        # Validate the ballot's part.
        part_data_list = data['parts']
        limit_value = 1
        if len(part_data_list) != limit_value:
            e = self.error_messages['exact_length'] % {'limit_value': limit_value}
            raise serializers.ValidationError({'parts': e})
        part_data = part_data_list[0]
        ballot_part = ballot.parts.all()[(BallotPart.TAG_A, BallotPart.TAG_B).index(part_data['tag'])]
        try:
            # If the vote-code type is short then validate the submitted
            # credential.
            if election.vote_code_type == election.VOTE_CODE_TYPE_SHORT:
                credential = part_data['credential']
                try:
                    credential = part_data['credential'] = base32.normalize(credential)
                except ValueError as e:
                    raise serializers.ValidationError({'credential': e})
                if len(credential) != election.credential_length:
                    e = self.error_messages['exact_length'] % {'limit_value': election.credential_length}
                    raise serializers.ValidationError({'credential': e})
                try:
                    hasher.verify(credential, ballot_part.credential_hash)
                except ValueError as e:
                    raise serializers.ValidationError({'credential': e})
            # Validate the part's questions.
            question_data_list = part_data['questions']
            limit_value = election.question_count
            if len(question_data_list) != limit_value:
                e = self.error_messages['exact_length'] % {'limit_value': limit_value}
                raise serializers.ValidationError({'questions': e})
            question_errors = []
            for question_index, question_data in enumerate(question_data_list):
                election_question = election.questions.all()[question_index]
                ballot_question = ballot_part.questions.all()[question_index]
                try:
                    # Validate the question's options.
                    option_data_list = question_data['options']
                    if len(option_data_list) < election_question.min_selection_count:
                        e = self.error_messages['min_length'] % {'limit_value': election_question.min_selection_count}
                        raise serializers.ValidationError({'options': e})
                    if len(option_data_list) > election_question.max_selection_count:
                        e = self.error_messages['max_length'] % {'limit_value': election_question.max_selection_count}
                        raise serializers.ValidationError({'options': e})
                    valid_option_indices = set(range(election_question.option_count))
                    option_errors = []
                    for option_data in option_data_list:
                        try:
                            # Ensure that the index is valid and unique.
                            index = option_data['index']
                            if index not in valid_option_indices:
                                raise serializers.ValidationError({'index': "Invalid or duplicate value."})
                            valid_option_indices.remove(index)
                            # If the vote-code type is long then validate the
                            # submitted vote-code, too.
                            if election.vote_code_type == election.VOTE_CODE_TYPE_LONG:
                                vote_code = option_data['vote_code']
                                try:
                                    vote_code = option_data['vote_code'] = base32.normalize(vote_code)
                                except ValueError as e:
                                    raise serializers.ValidationError({'vote_code': e})
                                if len(vote_code) != election.vote_code_length:
                                    e = self.error_messages['exact_length'] % {
                                        'limit_value': election.vote_code_length
                                    }
                                    raise serializers.ValidationError({'vote_code': e})
                                try:
                                    ballot_option = ballot_question.options.all()[index]
                                    hasher.verify(vote_code, ballot_option.vote_code_hash)
                                except ValueError as e:
                                    raise serializers.ValidationError({'credential': e})
                        except serializers.ValidationError as e:
                            option_errors.append(e.detail)
                        else:
                            option_errors.append({})
                    if any(option_errors):
                        raise serializers.ValidationError({'options': option_errors})
                except serializers.ValidationError as e:
                    question_errors.append(e.detail)
                else:
                    question_errors.append({})
            if any(question_errors):
                raise serializers.ValidationError({'questions': question_errors})
        except serializers.ValidationError as e:
            raise serializers.ValidationError({'parts': [e.detail]})
        return data

    def update(self, ballot, validated_data):
        election = self.context['election']
        part_data = validated_data['parts'][0]
        ballot_part = ballot.parts.all()[(BallotPart.TAG_A, BallotPart.TAG_B).index(part_data['tag'])]
        update_fields = []
        # Mark the ballot part as cast.
        ballot_part.is_cast = True
        update_fields.append('is_cast')
        if election.vote_code_type == election.VOTE_CODE_TYPE_SHORT:
            # Save the submitted credential.
            ballot_part.credential = part_data['credential']
            update_fields.append('credential')
        ballot_part.save(update_fields=update_fields)
        for ballot_question, question_data in zip(ballot_part.questions.all(), part_data['questions']):
            option_indices = [option_data['index'] for option_data in question_data['options']]
            if election.vote_code_type == election.VOTE_CODE_TYPE_SHORT:
                # Mark the submitted options as voted.
                ballot_question.options.filter(index__in=option_indices).update(is_voted=True)
            elif election.vote_code_type == election.VOTE_CODE_TYPE_LONG:
                # Mark the submitted options as voted and save their
                # vote-codes.
                for option_data in question_data['options']:
                    ballot_option = ballot_question.options.all()[option_data['index']]
                    ballot_option.vote_code = option_data['vote_code']
                    ballot_option.is_voted = True
                    ballot_option.save(update_fields=['vote_code', 'is_voted'])
        return ballot


def _validate_base64_list(v, l):
    if not isinstance(v, list) or len(v) != l:
        raise serializers.ValidationError("This value must be a list of %d base64-encoded strings." % l)
    try:
        for d in v:
            if six.PY2:
                if not re.match(b'^[A-Za-z0-9+/]*={0,2}$', d):
                    raise TypeError("Non-base64 digit found.")
                base64.b64decode(d)  # raises TypeError
            elif six.PY3:
                base64.b64decode(d, validate=True)  # raises binascii.Error
    except (TypeError, binascii.Error) as e:
        raise serializers.ValidationError(e)


class TallyUpdateElectionQuestionSerializer(serializers.ModelSerializer):
    tally_decommitment = serializers.JSONField(required=True)

    class Meta:
        model = BallotQuestion
        fields = ['tally_decommitment']


class TallyUpdateElectionSerializer(serializers.ModelSerializer):
    questions = TallyUpdateElectionQuestionSerializer(many=True, allow_empty=False)

    class Meta:
        model = BallotPart
        fields = ['questions']

    def __init__(self, *args, **kwargs):
        kwargs['partial'] = False  # all fields are always required
        super(TallyUpdateElectionSerializer, self).__init__(*args, **kwargs)
        self.trustee = self.instance.trustees.get(user=self.context['request'].user)

    def validate(self, data):
        data = super(TallyUpdateElectionSerializer, self).validate(data)
        election = self.instance
        # Check if this trustee has already submitted their partial tally
        # decommitment.
        if self.trustee.has_submitted_tally_decommitment:
            e = "You have already submitted the tally decommitment."
            raise serializers.ValidationError({api_settings.NON_FIELD_ERRORS_KEY: e})
        # Check if this trustee has submitted the decommitments/zk2 for all
        # cast ballots. Lock the ballots before checking.
        election.ballots.filter(parts__is_cast=True).select_for_update().exists()
        if not self.trustee.has_submitted_all_ballots:
            e = "You have not submitted all the ballots yet."
            raise serializers.ValidationError({api_settings.NON_FIELD_ERRORS_KEY: e})
        # Validate the election's questions.
        question_data_list = data['questions']
        limit_value = election.question_count
        if len(question_data_list) != limit_value:
            e = self.error_messages['exact_length'] % {'limit_value': limit_value}
            raise serializers.ValidationError({'questions': e})
        question_errors = []
        for question_index, question_data in enumerate(question_data_list):
            election_question = election.questions.all()[question_index]
            try:
                # `tally_decommitment` must be an empty list or a list of N
                # base64-encoded strings, where N is the number of non-blank
                # options.
                tally_decommitment = question_data['tally_decommitment']
                try:
                    _validate_base64_list(tally_decommitment, 0)
                except:
                    non_blank_option_count = election_question.option_count - election_question.blank_option_count
                    try:
                        _validate_base64_list(tally_decommitment, non_blank_option_count)
                    except serializers.ValidationError as e:
                        raise serializers.ValidationError({'tally_decommitment': e})
            except serializers.ValidationError as e:
                question_errors.append(e.detail)
            else:
                question_errors.append({})
        if any(question_errors):
            raise serializers.ValidationError({'questions': question_errors})
        return data

    def update(self, election, validated_data):
        for election_question, question_data in zip(election.questions.all(), validated_data['questions']):
            tally_decommitment = question_data['tally_decommitment']
            election_question.partial_tally_decommitments.create(trustee=self.trustee, value=tally_decommitment)
        # If all trustees have submitted their tally decommitments then start
        # the task to generate the results.
        if election.questions.all()[0].partial_tally_decommitments.count() == election.trustees.count():
            transaction.on_commit(lambda: generate_election_results.delay(election.pk))
        return election


class TallyUpdateBallotOptionSerializer(serializers.ModelSerializer):
    decommitment = serializers.JSONField(required=False)
    zk2 = serializers.JSONField(required=False)

    class Meta:
        model = BallotOption
        fields = ['decommitment', 'zk2']


class TallyUpdateBallotQuestionSerializer(serializers.ModelSerializer):
    options = TallyUpdateBallotOptionSerializer(many=True, allow_empty=True)
    zk2 = serializers.JSONField(required=False)

    class Meta:
        model = BallotQuestion
        fields = ['options', 'zk2']


class TallyUpdateBallotPartSerializer(serializers.ModelSerializer):
    questions = TallyUpdateBallotQuestionSerializer(many=True, allow_empty=False)

    class Meta:
        model = BallotPart
        fields = ['questions']


class TallyUpdateBallotSerializer(serializers.ModelSerializer):
    parts = TallyUpdateBallotPartSerializer(many=True, allow_empty=False)

    def __init__(self, *args, **kwargs):
        kwargs['partial'] = False  # all fields are always required
        super(TallyUpdateBallotSerializer, self).__init__(*args, **kwargs)
        election = self.context['election']
        self.trustee = election.trustees.get(user=self.context['request'].user)

    class Meta:
        model = Ballot
        fields = ['parts']

    def validate(self, data):
        data = super(TallyUpdateBallotSerializer, self).validate(data)
        election = self.context['election']
        ballot = self.instance
        # Check if this trustee has already submitted the tally decommitment.
        # The trustees can re-submit a ballot multiple times until the tally
        # decommitment is submitted.
        if self.trustee.has_submitted_tally_decommitment:
            e = "You have already submitted the tally decommitment."
            raise serializers.ValidationError({api_settings.NON_FIELD_ERRORS_KEY: e})
        # Check if this ballot has not been cast.
        if not any(ballot_part.is_cast for ballot_part in ballot.parts.all()):
            e = "This ballot has not been cast."
            raise serializers.ValidationError({api_settings.NON_FIELD_ERRORS_KEY: e})
        # Validate the ballot's parts.
        part_data_list = data['parts']
        limit_value = 2
        if len(part_data_list) != limit_value:
            e = self.error_messages['exact_length'] % {'limit_value': limit_value}
            raise serializers.ValidationError({'parts': e})
        part_errors = []
        for part_index, part_data in enumerate(part_data_list):
            ballot_part = ballot.parts.all()[part_index]
            try:
                # Validate the part's questions.
                question_data_list = part_data['questions']
                limit_value = election.question_count
                if len(question_data_list) != limit_value:
                    e = self.error_messages['exact_length'] % {'limit_value': limit_value}
                    raise serializers.ValidationError({'questions': e})
                question_errors = []
                for question_index, question_data in enumerate(question_data_list):
                    election_question = election.questions.all()[question_index]
                    try:
                        option_count = election_question.option_count
                        non_blank_option_count = option_count - election_question.blank_option_count
                        if ballot_part.is_cast:
                            if 'zk2' not in question_data:
                                e = self.error_messages['required']
                                raise serializers.ValidationError({'zk2': e})
                            # `zk2` must be a list of N base64-encoded strings,
                            # where N is the three times the number of options
                            # plus the number of non-blank options.
                            zk2 = question_data['zk2']
                            try:
                                _validate_base64_list(zk2, 3 * option_count + non_blank_option_count)
                            except ValueError as e:
                                raise serializers.ValidationError({'zk2': e})
                        # Validate the question's options.
                        option_data_list = question_data['options']
                        limit_value = election_question.option_count
                        if len(option_data_list) != limit_value:
                            e = self.error_messages['exact_length'] % {'limit_value': limit_value}
                            raise serializers.ValidationError({'options': e})
                        option_errors = []
                        for option_data in option_data_list:
                            try:
                                if ballot_part.is_cast:
                                    if 'zk2' not in option_data:
                                        e = self.error_messages['required']
                                        raise serializers.ValidationError({'zk2': e})
                                    # `zk2` must be a list of N base64-encoded
                                    # strings, where N is the three times the
                                    # number of non-blank options.
                                    zk2 = option_data['zk2']
                                    try:
                                        _validate_base64_list(zk2, 3 * non_blank_option_count)
                                    except ValueError as e:
                                        raise serializers.ValidationError({'zk2': e})
                                else:
                                    if 'decommitment' not in option_data:
                                        e = self.error_messages['required']
                                        raise serializers.ValidationError({'decommitment': e})
                                    # `decommitment` must be a list of N base64
                                    # encoded strings, where N is the number of
                                    # non-blank options.
                                    decommitment = option_data['decommitment']
                                    try:
                                        _validate_base64_list(decommitment, non_blank_option_count)
                                    except ValueError as e:
                                        raise serializers.ValidationError({'decommitment': e})
                            except serializers.ValidationError as e:
                                option_errors.append(e.detail)
                            else:
                                option_errors.append({})
                        if any(option_errors):
                            raise serializers.ValidationError({'options': option_errors})
                    except serializers.ValidationError as e:
                        question_errors.append(e.detail)
                    else:
                        question_errors.append({})
                if any(question_errors):
                    raise serializers.ValidationError({'questions': question_errors})
            except serializers.ValidationError as e:
                part_errors.append(e.detail)
            else:
                part_errors.append({})
        if any(part_errors):
            raise serializers.ValidationError({'parts': part_errors})
        return data

    def update(self, ballot, validated_data):
        for ballot_part, part_data in zip(ballot.parts.all(), validated_data['parts']):
            for ballot_question, question_data in zip(ballot_part.questions.all(), part_data['questions']):
                if ballot_part.is_cast:
                    zk2 = question_data['zk2']
                    self.trustee.partial_question_zk2.filter(ballot_question=ballot_question).delete()
                    self.trustee.partial_question_zk2.create(ballot_question=ballot_question, value=zk2)
                for ballot_option, option_data in zip(ballot_question.options.all(), question_data['options']):
                    if ballot_part.is_cast:
                        zk2 = option_data['zk2']
                        self.trustee.partial_option_zk2.filter(ballot_option=ballot_option).delete()
                        self.trustee.partial_option_zk2.create(ballot_option=ballot_option, value=zk2)
                    else:
                        decommitment = option_data['decommitment']
                        self.trustee.partial_decommitments.filter(ballot_option=ballot_option).delete()
                        self.trustee.partial_decommitments.create(ballot_option=ballot_option, value=decommitment)
        return ballot
