# File: serializers.py

from __future__ import absolute_import, division, print_function, unicode_literals

from rest_framework import serializers
from rest_framework.reverse import reverse

from rest_framework_nested import serializers as nested_serializers

from demos_voting.bulletin_board.models import Election, Question, Option, Ballot, Part, PQuestion, POption


class OptionSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Option
        fields = ['index', 'name', 'vote_count']


class QuestionSerializer(serializers.HyperlinkedModelSerializer):

    options = OptionSerializer(many=True)

    class Meta:
        model = Question
        fields = ['index', 'name', 'min_choices', 'max_choices', 'commitment_key', 'options']


class ElectionSerializer(serializers.HyperlinkedModelSerializer):

    certificate_url = serializers.SerializerMethodField()
    questions = QuestionSerializer(many=True)

    ballots_url = serializers.HyperlinkedIdentityField(
        view_name='bulletin_board-api:ballot-list',
        lookup_field='id',
        lookup_url_kwarg='election_id'
    )

    def get_certificate_url(self, obj):
        if obj.certificate:
            return reverse(
                viewname='bulletin_board-media:certificate',
                kwargs={'election_id': obj.id},
                request=self.context['request']
            )

    class Meta:
        model = Election
        fields = [
            'url', 'ballots_url', 'id', 'name', 'voting_starts_at', 'voting_ends_at', 'state', 'type', 'votecode_type',
            'security_code_type', 'ballot_count', 'credential_length', 'votecode_length', 'receipt_length',
            'security_code_length', 'curve_name', 'certificate_url', 'coins', 'questions'
        ]
        extra_kwargs = {
            'url': {
                'view_name': 'bulletin_board-api:election-detail',
                'lookup_field': 'id',
            },
        }


class POptionSerializer(serializers.HyperlinkedModelSerializer):

    commitment = serializers.JSONField()
    zk1 = serializers.JSONField()

    def to_representation(self, obj):
        data = super(POptionSerializer, self).to_representation(obj)
        if obj.election.state == Election.STATE_VOTING_STARTED:
            data['is_voted'] = obj._meta.get_field('is_voted').default
            if obj.election.votecode_type == Election.VOTECODE_TYPE_LONG:
                data['votecode'] = obj._meta.get_field('votecode').default
        return data

    class Meta:
        model = POption
        fields = ['index', 'is_voted', 'votecode', 'votecode_hash', 'receipt', 'commitment', 'zk1']


class PQuestionSerializer(serializers.HyperlinkedModelSerializer):

    index = serializers.IntegerField()
    zk = serializers.JSONField()
    options = POptionSerializer(many=True)

    class Meta:
        model = PQuestion
        fields = ['index', 'zk', 'options']


class PartSerializer(serializers.HyperlinkedModelSerializer):

    questions = PQuestionSerializer(many=True)

    class Meta:
        model = Part
        fields = ['tag', 'questions']


class BallotSerializer(nested_serializers.NestedHyperlinkedModelSerializer):

    election_url = serializers.HyperlinkedRelatedField(
        view_name='bulletin_board-api:election-detail',
        lookup_field='id',
        source='election',
        read_only=True
    )

    parts = PartSerializer(many=True)

    def to_representation(self, obj):
        data = super(BallotSerializer, self).to_representation(obj)
        if obj.election.state == Election.STATE_VOTING_STARTED:
            data['credential'] = obj._meta.get_field('credential').default
        return data

    class Meta:
        model = Ballot
        fields = ['url', 'election_url', 'serial_number', 'credential', 'credential_hash', 'parts']
        extra_kwargs = {
            'url': {
                'view_name': 'bulletin_board-api:ballot-detail',
                'lookup_field': 'serial_number',
                'parent_lookup_field': 'election',
                'parent_lookup_related_field': 'id',
                'parent_lookup_url_kwarg': 'election_id',
            }
        }

