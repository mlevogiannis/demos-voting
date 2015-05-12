# File: serializers.py

from django.db.models import Model
from django.db.models.query import QuerySet
from django.core.serializers.json import Serializer


class JsonSerializer(Serializer):
	
	srv_dict = {
		
		'ea': {
			'Election': ['election_id', 'text', 'ballots', 'start_datetime',
				'end_datetime', 'state'],
			'Question': ['election', 'question_id', 'text', 'key'],
			'Option': ['question', 'text', 'order'],
			'Ballot': ['election', 'ballot_id', 'credential_hash'],
			'Side': ['ballot', 'side_id', 'permindex_hash'],
			'OptData': ['side', 'question', 'votecode', 'receipt', 'com',
				'decom', 'zk1', 'zk_state', 'order'],
			'Trustee': ['election', 'email'],
		},
		
		'bds': {
			'Election': ['election_id', 'text', 'ballots', 'start_datetime',
				'end_datetime', 'state'],
			'Ballot': ['election', 'ballot_id', 'pdf'],
			'Side': ['ballot', 'side_id', 'permindex', 'voteurl'],
			'Trustee': ['election', 'email'],
		},
		
		'abb': {
			'Election': ['election_id', 'text', 'ballots', 'start_datetime',
				'end_datetime', 'state'],
			'Question': ['election', 'question_id', 'text', 'key'],
			'Option': ['question', 'text', 'order'],
			'Ballot': ['election', 'ballot_id'],
			'Side': ['ballot', 'side_id', 'permindex'],
			'OptData': ['side', 'question', 'votecode', 'receipt', 'com', 'zk1',
				'zk2', 'voted', 'order'],
		},
		
		'vbb': {
			'Election': ['election_id', 'text', 'ballots', 'start_datetime',
				'end_datetime', 'state'],
			'Question': ['election', 'question_id', 'text'],
			'Option': ['question', 'text', 'order'],
			'Ballot': ['election', 'ballot_id', 'credential_hash'],
			'Side': ['ballot', 'side_id', 'permindex_hash', 'permindex'],
			'OptData': ['side', 'question', 'votecode', 'receipt', 'voted',
				'order'],
		},
	}
	
	app_prefix = 'demos_'
	
	def end_object(self, obj):
		
		for field, value_list in self.extra_fields.items():
			self._current[field] = value_list.pop(0)
		
		super().end_object(obj)
	
	def serialize(self, queryset, **options):
		
		if isinstance(queryset, QuerySet):
			model = queryset.model
		elif isinstance(queryset, Model):
			model = queryset.__class__
			queryset = [queryset]
		else:
			raise ValueError("Expected object or queryset")
		
		options.setdefault('indent', None)
		options.setdefault('separators', (',', ':'))
		options.setdefault('use_natural_foreign_keys', True)
		options.setdefault('use_natural_primary_keys', True)
		
		srv = options.pop('srv', None)
		fields = options.pop('fields', None)
		
		self.extra_fields = options.pop('extra_fields', None) or {}
		
		if srv is not None:
			
			model_dict = self.srv_dict[srv]
			field_list = model_dict[model.__name__]
			
			fields = tuple(set(fields) & set(field_list)) \
				if fields is not None else tuple(field_list)
			
			app_label = model._meta.app_label
			model._meta.app_label = self.app_prefix + srv
		
		if fields is not None:
			
			self.extra_fields = {field: list(value_list) for field, value_list
				in self.extra_fields.items() if field in fields}
			
			options['fields'] = tuple(set(fields) - set(self.extra_fields))
		
		value = super().serialize(queryset, **options)
		
		if srv is not None:
			model._meta.app_label = app_label
		
		self.extra_fields = {}
		
		return value

