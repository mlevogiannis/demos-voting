from __future__ import absolute_import, division, print_function, unicode_literals

import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

from django.core.validators import MaxLengthValidator
from django.utils.encoding import force_bytes

from rest_framework import serializers
from rest_framework.settings import api_settings

from six.moves import zip

from demos_voting.base.models import BaseBallotPart, BaseElection
from demos_voting.base.utils import base32, hasher


class DynamicFieldsMixin(object):
    """
    A serializer mixin that takes an additional `fields` argument that controls
    which fields will be included in the serializer and which not. The `fields`
    argument may be a sequence (list, set, tuple) or a mapping (dict). If it is
    a sequence then only the fields that are specified are included and nested
    serializers are not supported. If it is a mapping then the fields must be
    marked either to be included (True) or to be excluded (False) and nested
    serializers are supported. Fields that are not specified are assumed to be
    excluded or included, respectively. E.g.:
    fields = ['name', 'slug', ...]
    fields = {
        'name': True,
        'slug': True,
        'questions': {
            'name': False,
            ...
        }
    }
    """

    def __init__(self, *args, **kwargs):
        assert isinstance(self, serializers.Serializer)
        fields = kwargs.pop('fields', None)
        super(DynamicFieldsMixin, self).__init__(*args, **kwargs)
        if fields is not None:
            if isinstance(fields, (list, set, tuple)):
                included_fields = set(fields)
                serializer_fields = set(self.fields.keys())
                for field_name in serializer_fields - included_fields:
                    self.fields.pop(field_name)
            elif isinstance(fields, dict):
                def _update_serializer_fields(serializer, fields):
                    if isinstance(serializer, serializers.ListSerializer):
                        serializer = serializer.child
                    serializer_fields = set(serializer.fields.keys())
                    included_fields = set()
                    excluded_fields = set()
                    nested_fields = set()
                    for field_name, value in fields.items():
                        if field_name not in serializer_fields:
                            raise ValueError("Field `%s` does not exist." % field_name)
                        else:
                            if value is True:
                                included_fields.add(field_name)
                            elif value is False:
                                excluded_fields.add(field_name)
                            elif isinstance(value, dict):
                                nested_fields.add(field_name)
                            else:
                                raise ValueError("Value `%s` is not valid for field `%s`." % (value, field_name))
                    if included_fields and excluded_fields:
                        raise ValueError("Fields must be marked either to be included (True) or excluded (False).")
                    for field_name in (excluded_fields or (serializer_fields - (included_fields | nested_fields))):
                        serializer.fields.pop(field_name)
                    for field_name in nested_fields:
                        field = serializer.fields[field_name]
                        if not isinstance(field, serializers.BaseSerializer):
                            raise ValueError("Field `%s` is not a nested serializer." % field_name)
                        _update_serializer_fields(field, fields[field_name])

                _update_serializer_fields(self, fields)
            else:
                raise ValueError("The `fields` argument must be a sequence or a mapping.")


# Creation mixins #############################################################

class CreateElectionMixin(object):
    default_error_messages = {
        'blank': "This field may not be blank.",
        'not_blank': "This field must be blank.",
        'null': "This field may not be null.",
        'not_null': "This field must be null.",
        'max_value': "This value must be less than or equal to %(limit_value)s.",
        'exact_value': "This value must be exactly %(limit_value)s.",
    }

    def validate(self, data):
        data = super(CreateElectionMixin, self).validate(data)
        type = data['type']
        vote_code_type = data['vote_code_type']
        # `vote_code_length` must be null if the vote-code type is short,
        # or not null if the vote-code type is long.
        vote_code_length = data['vote_code_length']
        if vote_code_type == BaseElection.VOTE_CODE_TYPE_SHORT:
            if vote_code_length is not None:
                raise serializers.ValidationError({'vote_code_length': self.error_messages['not_null']})
        elif vote_code_type == BaseElection.VOTE_CODE_TYPE_LONG:
            if vote_code_length is None:
                raise serializers.ValidationError({'vote_code_length': self.error_messages['null']})
        # If the vote-code type is short then `security_code_length` may be an
        # integer or null. If the vote-code type is long then it must be null.
        security_code_length = data['security_code_length']
        if vote_code_type == BaseElection.VOTE_CODE_TYPE_LONG:
            if security_code_length is not None:
                raise serializers.ValidationError({'security_code_length': self.error_messages['not_null']})
        # The start time cannot be after the end time.
        if data['voting_starts_at'] >= data['voting_ends_at']:
            e = "`voting_starts_at` cannot be greater than or equal to `voting_ends_at`."
            raise serializers.ValidationError({api_settings.NON_FIELD_ERRORS_KEY: e})
        # `certificate_file` must be null if the vote-code type is short or not
        # null if the vote-code type is long
        if 'certificate_file' in self.fields:  # optional field
            certificate_file = data['certificate_file']
            if vote_code_type == BaseElection.VOTE_CODE_TYPE_SHORT:
                if certificate_file:
                    raise serializers.ValidationError({'certificate_file': self.error_messages['not_blank']})
            elif vote_code_type == BaseElection.VOTE_CODE_TYPE_LONG:
                if not certificate_file:
                    raise serializers.ValidationError({'certificate_file': self.error_messages['blank']})
        # Validate the questions.
        question_data_list = data['questions']
        question_fields = self.fields['questions'].child.fields
        question_errors = []
        for question_index, question_data in enumerate(question_data_list):
            try:
                # `index` is 0-based and cannot be greater than the total
                # number of questions minus 1.
                index = question_data['index']
                if index != question_index:
                    e = self.error_messages['exact_value'] % {'limit_value': question_index}
                    raise serializers.ValidationError({'index': e})
                # `name` must be a non-empty string if the election type is
                # question-option or blank if the election type is
                # party-candidate.
                name = question_data['name']
                if type == BaseElection.TYPE_QUESTION_OPTION:
                    if not name:
                        raise serializers.ValidationError({'name': self.error_messages['blank']})
                elif type == BaseElection.TYPE_PARTY_CANDIDATE:
                    if name:
                        raise serializers.ValidationError({'name': self.error_messages['not_blank']})
                # If the election type is question-option then the minimum
                # number of selections cannot be greater than the total number
                # of options minus 1, otherwise the voters would be forced to
                # vote for every option. If the election type is party-
                # candidate then this value has no meaning and must be equal to
                # the maximum number of selections (to be validated later).
                min_selection_count = question_data['min_selection_count']
                if type == BaseElection.TYPE_QUESTION_OPTION:
                    limit_value = len(question_data['options']) - 1
                    if min_selection_count > limit_value:
                        e = self.error_messages['max_value'] % {'limit_value': limit_value}
                        raise serializers.ValidationError({'min_selection_count': e})
                # If the election type is question-option then the maximum
                # number of selections cannot be greater than the total number
                # of options. If the election type is party-candidate and this
                # is the party question (index is 0) then this value must be
                # equal to 1. If the election type is party-candidate and this
                # is the candidate question (index is 1) then this value cannot
                # be greater than the number of candidates per party minus 1
                # (all parties have the same number of candidates including the
                # blank candidates).
                max_selection_count = question_data['max_selection_count']
                if type == BaseElection.TYPE_QUESTION_OPTION:
                    limit_value = len(question_data['options'])
                    if max_selection_count > limit_value:
                        e = self.error_messages['max_value'] % {'limit_value': limit_value}
                        raise serializers.ValidationError({'max_selection_count': e})
                elif type == BaseElection.TYPE_PARTY_CANDIDATE:
                    if index == 0:
                        limit_value = 1
                        if max_selection_count != limit_value:
                            e = self.error_messages['exact_value'] % {'limit_value': limit_value}
                            raise serializers.ValidationError({'max_selection_count': e})
                    elif index == 1:
                        party_count = len(data['questions'][0]['options'])  # this has already been validated
                        candidate_count = len(question_data['options'])
                        candidate_per_party_count = candidate_count // party_count
                        limit_value = candidate_per_party_count - 1
                        if max_selection_count > limit_value:
                            e = self.error_messages['max_value'] % {'limit_value': limit_value}
                            raise serializers.ValidationError({'max_selection_count': e})
                # If the election type is question-option then the minimum
                # number of selections cannot be greater than the maximum
                # number of selections. If the election type is party-candidate
                # then the minimum and the maximum numbers of selections must
                # be equal.
                if type == BaseElection.TYPE_QUESTION_OPTION:
                    if min_selection_count > max_selection_count:
                        e = "`min_selection_count` cannot be greater than `max_selection_count`."
                        raise serializers.ValidationError({api_settings.NON_FIELD_ERRORS_KEY: e})
                elif type == BaseElection.TYPE_PARTY_CANDIDATE:
                    if min_selection_count != max_selection_count:
                        e = "`min_selection_count` must be equal to `max_selection_count`."
                        raise serializers.ValidationError({api_settings.NON_FIELD_ERRORS_KEY: e})
                # Validate the options.
                option_data_list = question_data['options']
                option_fields = question_fields['options'].child.fields
                option_errors = []
                for option_index, option_data in enumerate(option_data_list):
                    try:
                        # `index` is 0-based and cannot be greater than the
                        # total number of options minus 1.
                        index = option_data['index']
                        if index != option_index:
                            e = self.error_messages['exact_value'] % {'limit_value': option_index}
                            raise serializers.ValidationError({'index': e})
                        # `name` must be a non-empty string if the election
                        # type is question-option or it may be blank if the
                        # election type is party-candidate.
                        name = option_data['name']
                        if type == BaseElection.TYPE_QUESTION_OPTION:
                            if not name:
                                raise serializers.ValidationError({'name': self.error_messages['blank']})
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
        return data

    def create(self, validated_data):
        app_config = self.Meta.model._meta.app_config
        election_data = validated_data
        question_data_list = election_data.pop('questions')
        option_data_lists = []
        for question_data in question_data_list:
            option_data_list = question_data.pop('options')
            option_data_lists.append(option_data_list)
        administrator_data_list = election_data.pop('administrators')
        # Create the election object.
        election_model = app_config.get_model('Election')
        election = election_model.objects.create(**election_data)
        # Create the question objects.
        election_question_model = app_config.get_model('ElectionQuestion')
        election_questions = election_question_model.objects.bulk_create([
            election_question_model(election=election, **question_data)
            for question_data in question_data_list
        ])
        if election_questions[0].pk is None:
            pk_list = election_question_model.objects.filter(election=election).values_list('pk', flat=True)
            for election_question, pk in zip(election_questions, pk_list):
                election_question.pk = pk
        # Create the option objects.
        election_option_model = app_config.get_model('ElectionOption')
        election_option_model.objects.bulk_create([
            election_option_model(question=election_question, **option_data)
            for election_question, option_data_list in zip(election_questions, option_data_lists)
            for option_data in option_data_list
        ])
        # Create the administrator objects. Do not use bulk_create to ensure
        # that BaseElectionUser's overridden `save()` method will be called.
        for administrator_data in administrator_data_list:
            election.administrators.create(**administrator_data)
        return election


class CreateBallotListMixin(object):
    default_error_messages = {
        'max_length': "This value's length must be at most %(limit_value)s.",
    }

    def __init__(self, *args, **kwargs):
        super(CreateBallotListMixin, self).__init__(*args, **kwargs)
        election = self.context['election']
        remaining_ballots = election.ballot_count - election.ballots.count()
        self.validators.append(MaxLengthValidator(remaining_ballots, message=self.error_messages['max_length']))


class CreateBallotMixin(object):
    default_error_messages = {
        'blank': "This field may not be blank.",
        'not_blank': "This field must be blank.",
        'null': "This field may not be null.",
        'not_null': "This field must be null.",
        'min_length': "This value's length must be at least %(limit_value)s.",
        'exact_length': "This value's length must be exactly %(limit_value)s.",
        'max_value': "This value must be less than or equal to %(limit_value)s.",
        'exact_value': "This value must be exactly %(limit_value)s.",
    }

    def validate(self, data):
        data = super(CreateBallotMixin, self).validate(data)
        election = self.context['election']
        # The maximum serial number is 100 plus the total number of ballots
        # minus 1.
        serial_number = data['serial_number']
        limit_value = 100 + election.ballot_count - 1
        if serial_number > limit_value:
            e = self.error_messages['max_value'] % {'limit_value': limit_value}
            raise serializers.ValidationError({'serial_number': e})
        # Validate the ballot's parts.
        part_data_list = data['parts']
        limit_value = 2
        if len(part_data_list) != limit_value:
            e = self.error_messages['exact_length'] % {'limit_value': limit_value}
            raise serializers.ValidationError({'parts': e})
        part_fields = self.fields['parts'].child.fields
        part_errors = []
        for part_tag, part_data in zip((BaseBallotPart.TAG_A, BaseBallotPart.TAG_B), part_data_list):
            try:
                # `tag` must be A or B.
                tag = part_data['tag']
                if tag != part_tag:
                    e = self.error_messages['exact_value'] % {'limit_value': part_tag}
                    raise serializers.ValidationError({'tag': e})
                # `credential` must be a fixed-length, base32-encoded string.
                if 'credential' in part_fields:  # optional field
                    credential = part_data['credential']
                    if not credential:
                        raise serializers.ValidationError({'credential': self.error_messages['blank']})
                    else:
                        try:
                            credential = part_data['credential'] = base32.normalize(credential)
                        except ValueError as e:
                            raise serializers.ValidationError({'credential': e})
                        else:
                            limit_value = election.credential_length
                            if len(credential) != limit_value:
                                e = self.error_messages['exact_length'] % {'limit_value': limit_value}
                                raise serializers.ValidationError({'credential': e})
                # Check if the credential hash is supported.
                if 'credential_hash' in part_fields:  # optional field
                    credential_hash = part_data['credential_hash']
                    try:
                        hasher.summary(credential_hash)
                    except (AssertionError, ValueError):
                        e = "Invalid hash."
                        raise serializers.ValidationError({'credential_hash': e})
                # If the vote-code type is short then `security_code` may be
                # an integer or null. If the vote-code type is long then then
                # `security_code` must be null.
                if 'security_code' in part_fields:  # optional field
                    security_code = part_data['security_code']
                    if election.vote_code_type == election.VOTE_CODE_TYPE_SHORT:
                        if election.security_code_length is None:
                            if security_code:
                                raise serializers.ValidationError({'security_code': self.error_messages['not_blank']})
                        else:
                            if not security_code:
                                raise serializers.ValidationError({'security_code': self.error_messages['blank']})
                            else:
                                if not re.match(r'^[0-9]{%d}$' % election.security_code_length, security_code):
                                    e = "This value must be an integer with %d digits." % election.security_code_length
                                    raise serializers.ValidationError({'security_code': e})
                    elif election.vote_code_type == election.VOTE_CODE_TYPE_LONG:
                        if security_code:
                            raise serializers.ValidationError({'security_code': self.error_messages['not_blank']})
                # Validate the part's questions.
                question_data_list = part_data['questions']
                limit_value = election.question_count
                if len(question_data_list) != limit_value:
                    e = self.error_messages['exact_length'] % {'limit_value': limit_value}
                    raise serializers.ValidationError({'questions': e})
                question_fields = part_fields['questions'].child.fields
                question_errors = []
                for question_index, question_data in enumerate(question_data_list):
                    election_question = election.questions.all()[question_index]
                    non_blank_option_count = election_question.option_count - election_question.blank_option_count
                    try:
                        # `zk1` must be a list of N elements, where N is the
                        # number of non-blank options.
                        if 'zk1' in question_fields:  # optional field
                            zk1 = question_data['zk1']
                            limit_value = non_blank_option_count
                            if len(zk1) != limit_value:
                                e = self.error_messages['exact_length'] % {'limit_value': limit_value}
                                raise serializers.ValidationError({'zk1': e})
                        # Validate the question's options.
                        option_data_list = question_data['options']
                        limit_value = election.questions.all()[question_index].option_count
                        if len(option_data_list) != limit_value:
                            e = self.error_messages['exact_length'] % {'limit_value': limit_value}
                            raise serializers.ValidationError({'options': e})
                        option_fields = question_fields['options'].child.fields
                        option_errors = []
                        for option_index, option_data in enumerate(option_data_list):
                            try:
                                # `index` is 0-based and cannot be greater than
                                # the total number of options minus 1.
                                index = option_data['index']
                                if index != option_index:
                                    e = self.error_messages['exact_value'] % {'limit_value': option_index}
                                    raise serializers.ValidationError({'index': e})
                                # `vote_code` must be an integer in range 1 to
                                # the number of options if the vote-code type
                                # is short or a fixed length, base32-encoded
                                # string if the vote-code type is long.
                                if 'vote_code' in option_fields:  # optional field
                                    vote_code = option_data['vote_code']
                                    if election.vote_code_type == election.VOTE_CODE_TYPE_SHORT:
                                        if not vote_code:
                                            e = self.error_messages['blank']
                                            raise serializers.ValidationError({'vote_code': e})
                                        else:
                                            if not re.match(r'^[1-9][0-9]*$', vote_code):
                                                e = "This value must be a positive integer."
                                                raise serializers.ValidationError({'vote_code': e})
                                            limit_value = len(option_data_list)
                                            if int(vote_code) > limit_value:
                                                e = self.error_messages['max_value'] % {'limit_value': limit_value}
                                                raise serializers.ValidationError({'vote_code': e})
                                    elif election.vote_code_type == election.VOTE_CODE_TYPE_LONG:
                                        try:
                                            vote_code = option_data['vote_code'] = base32.normalize(vote_code)
                                        except ValueError as e:
                                            raise serializers.ValidationError({'vote_code': e})
                                        else:
                                            limit_value = election.vote_code_length
                                            if len(vote_code) != limit_value:
                                                e = self.error_messages['exact_length'] % {'limit_value': limit_value}
                                                raise serializers.ValidationError({'vote_code': e})
                                # `vote_code_hash` must be blank if the vote-code type is
                                # short or of a supported hash scheme if the vote-code type
                                # is long.
                                if 'vote_code_hash' in option_fields:  # optional field
                                    vote_code_hash = option_data['vote_code_hash']
                                    if election.vote_code_type == election.VOTE_CODE_TYPE_SHORT:
                                        if vote_code_hash:
                                            e = self.error_messages['not_blank']
                                            raise serializers.ValidationError({'vote_code_hash': e})
                                    elif election.vote_code_type == election.VOTE_CODE_TYPE_LONG:
                                        if not vote_code_hash:
                                            e = self.error_messages['blank']
                                            raise serializers.ValidationError({'vote_code_hash': e})
                                        else:
                                            try:
                                                hasher.summary(vote_code_hash)
                                            except (AssertionError, ValueError) as e:
                                                e = "Invalid hash."
                                                raise serializers.ValidationError({'vote_code_hash': e})
                                # `receipt` has a fixed length. If the vote-
                                # code type is long, its length is equal to the
                                # length of the signature algorithm's output
                                # that is used.
                                receipt = option_data['receipt']
                                try:
                                    receipt = option_data['receipt'] = base32.normalize(receipt)
                                except ValueError as e:
                                    raise serializers.ValidationError({'receipt': e})
                                else:
                                    if election.vote_code_type == election.VOTE_CODE_TYPE_SHORT:
                                        limit_value = election.receipt_length
                                        if len(receipt) != limit_value:
                                            e = self.error_messages['exact_length'] % {'limit_value': limit_value}
                                            raise serializers.ValidationError({'receipt': e})
                                    elif election.vote_code_type == election.VOTE_CODE_TYPE_LONG:
                                        public_key = election.certificate.public_key()
                                        limit_value = (public_key.key_size + 4) // 5
                                        if len(receipt) != limit_value:
                                            e = self.error_messages['exact_length'] % {'limit_value': limit_value}
                                            raise serializers.ValidationError({'receipt': e})
                                        # If the vote-code field exists then
                                        # the signature, too.
                                        if 'vote_code' in option_fields:
                                            signature = base32.decode_to_bytes(receipt, (public_key.key_size + 7) // 8)
                                            try:
                                                public_key.verify(
                                                    signature=signature,
                                                    data=force_bytes(vote_code),
                                                    padding=padding.PKCS1v15(),
                                                    algorithm=hashes.SHA256(),
                                                )
                                            except InvalidSignature:
                                                e = "Invalid receipt."
                                                raise serializers.ValidationError({'receipt': e})
                                # `commitment` must be a list of N elements,
                                # where N is the number of non-blank options.
                                if 'commitment' in option_fields:  # optional field
                                    commitment = option_data['commitment']
                                    limit_value = non_blank_option_count
                                    if len(commitment) != limit_value:
                                        e = self.error_messages['exact_length'] % {'limit_value': limit_value}
                                        raise serializers.ValidationError({'commitment': e})
                                # `zk1` must be a list of N elements, where N
                                # is the number of non-blank options plus 1.
                                if 'zk1' in option_fields:  # optional field
                                    zk1 = option_data['zk1']
                                    limit_value = non_blank_option_count + 1
                                    if len(zk1) != limit_value:
                                        e = self.error_messages['exact_length'] % {'limit_value': limit_value}
                                        raise serializers.ValidationError({'zk1': e})
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

    def create(self, validated_data):
        election = self.context['election']
        app_config = self.Meta.model._meta.app_config
        ballot_data = validated_data
        part_data_lists = []
        question_data_lists = []
        option_data_lists = []
        part_data_list = ballot_data.pop('parts')
        part_data_lists.append(part_data_list)
        for part_data in part_data_list:
            question_data_list = part_data.pop('questions')
            question_data_lists.append(question_data_list)
            for question_data in question_data_list:
                option_data_list = question_data.pop('options')
                option_data_lists.append(option_data_list)
        # Create the ballot objects.
        ballot_model = app_config.get_model('Ballot')
        ballot = ballot_model.objects.create(election=election, **ballot_data)
        # Create the part objects.
        ballot_part_model = app_config.get_model('BallotPart')
        ballot_parts = ballot_part_model.objects.bulk_create([
            ballot_part_model(ballot=ballot, **part_data)
            for part_data in part_data_list
        ])
        if ballot_parts[0].pk is None:
            pk_list = ballot_part_model.objects.filter(ballot=ballot).values_list('pk', flat=True)
            for ballot_part, pk in zip(ballot_parts, pk_list):
                ballot_part.pk = pk
        # Create the question objects.
        ballot_question_model = app_config.get_model('BallotQuestion')
        ballot_questions = ballot_question_model.objects.bulk_create([
            ballot_question_model(part=ballot_part, election_question=election_question, **question_data)
            for ballot_part, question_data_list in zip(ballot_parts, question_data_lists)
            for election_question, question_data in zip(election.questions.all(), question_data_list)
        ])
        if ballot_questions[0].pk is None:
            pk_list = ballot_question_model.objects.filter(part__in=ballot_parts).values_list('pk', flat=True)
            for ballot_question, pk in zip(ballot_questions, pk_list):
                ballot_question.pk = pk
        # Create the option objects.
        ballot_option_model = app_config.get_model('BallotOption')
        ballot_option_model.objects.bulk_create([
            ballot_option_model(question=ballot_question, **option_data)
            for ballot_question, option_data_list in zip(ballot_questions, option_data_lists)
            for option_data in option_data_list
        ])
        return ballot
