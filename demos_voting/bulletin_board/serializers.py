# File: serializers.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django.db.models import Prefetch

from rest_framework import serializers
from rest_framework.reverse import reverse

from rest_framework_nested.serializers import NestedHyperlinkedModelSerializer

from demos_voting.base.serializers import DynamicFieldsMixin
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


class ElectionSerializer(DynamicFieldsMixin, serializers.HyperlinkedModelSerializer):

    ballots_url = serializers.HyperlinkedIdentityField(
        view_name='bulletin_board-api:ballot-list',
        lookup_field='id',
        lookup_url_kwarg='election_id'
    )
    certificate_url = serializers.SerializerMethodField()
    questions = QuestionSerializer(many=True)

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

    @classmethod
    def get_prefetch_queryset(cls, fields=None):
        serializer = cls(fields=fields)
        dependencies = {
            'url': ['id'],
            'ballots_url': ['id'],
            'certificate_url': ['id', 'certificate'],
        }
        return get_prefetch_queryset(serializer, dependencies)

    def get_certificate_url(self, obj):
        if obj.certificate:
            return reverse(
                viewname='bulletin_board-media:certificate',
                kwargs={'election_id': obj.id},
                request=self.context['request']
            )


class POptionSerializer(serializers.HyperlinkedModelSerializer):

    commitment = serializers.JSONField()
    zk1 = serializers.JSONField()

    class Meta:
        model = POption
        fields = ['index', 'is_voted', 'votecode', 'votecode_hash', 'receipt', 'commitment', 'zk1']

    def to_representation(self, obj):
        data = super(POptionSerializer, self).to_representation(obj)
        if obj.election.state == Election.STATE_VOTING:
            if 'is_voted' in self.fields:
                data['is_voted'] = obj._meta.get_field('is_voted').default
            if 'votecode' in self.fields and obj.election.votecode_type == Election.VOTECODE_TYPE_LONG:
                data['votecode'] = obj._meta.get_field('votecode').default
        return data


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


class BallotSerializer(DynamicFieldsMixin, NestedHyperlinkedModelSerializer):

    election_url = serializers.HyperlinkedRelatedField(
        view_name='bulletin_board-api:election-detail',
        lookup_field='id',
        source='election',
        read_only=True
    )
    parts = PartSerializer(many=True)

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

    @classmethod
    def get_prefetch_queryset(cls, fields=None):
        serializer = cls(fields=fields)
        dependencies = {
            'url': ['serial_number']
        }
        queryset = get_prefetch_queryset(serializer, dependencies)
        queryset = queryset.prefetch_related(
            Prefetch('election', Election.objects.only('id', 'state', 'votecode_type'))
        )
        return queryset

    def to_representation(self, obj):
        data = super(BallotSerializer, self).to_representation(obj)
        if obj.election.state == Election.STATE_VOTING:
            if 'credential' in self.fields:
                data['credential'] = obj._meta.get_field('credential').default
        return data


# Helper functions ------------------------------------------------------------

def get_prefetch_queryset(serializer, dependencies={}):
    """
    Return a QuerySet that will prefetch related objects and load only
    the subset of fields required by the specified serializer.
    """

    def _get_prefetch_queryset(serializer, dependencies={}, lookup_prefix=''):
        if isinstance(serializer, serializers.ListSerializer):
            serializer = serializer.child

        queryset = serializer.Meta.model.objects.all()
        prefetch_lookups = []

        model_fields = set()
        load_fields = set(['pk'])

        for field in queryset.model._meta.get_fields():
            if not field.auto_created and not field.is_relation:
                model_fields.add(field.name)
            elif field.many_to_one:
                load_fields.add(field.name)

        for field_name, field in serializer.fields.items():
            if isinstance(field, serializers.BaseSerializer):
                nested_lookup = '%s%s' % (lookup_prefix, field_name)
                nested_queryset, nested_prefetch_lookups = _get_prefetch_queryset(
                    field, dependencies.get(field_name, {}), '%s__' % nested_lookup
                )
                prefetch_lookups.append(Prefetch(nested_lookup, nested_queryset))
                prefetch_lookups.extend(nested_prefetch_lookups)
            else:
                if field_name in model_fields:
                    load_fields.add(field_name)
                if field_name in dependencies:
                    load_fields.update(dependencies[field_name])

        return queryset.only(*load_fields), prefetch_lookups

    queryset, prefetch_lookups = _get_prefetch_queryset(serializer, dependencies)
    queryset = queryset.prefetch_related(*prefetch_lookups)

    return queryset

