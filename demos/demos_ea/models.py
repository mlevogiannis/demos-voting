# File: models.py

from django.db import models
from django.core import urlresolvers

from demos_utils import enums, fields
from demos_utils.settings import *


class Config(models.Model):
	
	option_name = models.CharField(max_length=TEXT_LEN)
	option_value = models.CharField(max_length=TEXT_LEN)


class ElectionManager(models.Manager):
	
	def get_by_natural_key(self, election_id):
		return self.get(election_id=election_id)


class Election(models.Model):
	
	election_id = models.CharField(max_length=8, unique=True)
	
	text = models.CharField(max_length=TEXT_LEN)
	ballots = models.PositiveIntegerField()
	
	start_datetime = models.DateTimeField()
	end_datetime = models.DateTimeField()
	
	state = fields.IntEnumField(cls=enums.State)
	
	# Other model methods and meta options
	
	objects = ElectionManager()

	def natural_key(self):
		return (self.election_id,)
	
	def get_absolute_url(self):
		return urlresolvers.reverse('demos_ea:manage', args=[self.election_id])
	
	def __str__(self):
		return self.text


class QuestionManager(models.Manager):
	
	def get_by_natural_key(self, question_id, election_id):
		
		return self.get(question_id=question_id,
			election__election_id=election_id)


class Question(models.Model):
	
	election = models.ForeignKey(Election)
	
	question_id = models.PositiveSmallIntegerField()
	text = models.CharField(max_length=TEXT_LEN)
	
	key = fields.JsonField()
	
	# Other model methods and meta options
	
	objects = QuestionManager()

	def natural_key(self):
		return (self.question_id, ) + self.election.natural_key()
	
	def __str__(self):
		return self.text
	
	class Meta:
		unique_together = ('election', 'question_id')


class OptionManager(models.Manager):
	
	def get_by_natural_key(self, text, question_id, election_id):
		
		return self.get(text=text, question__question_id=question_id,
			question__election__election_id=election_id)


class Option(models.Model):
	
	question = models.ForeignKey(Question)
	
	text = models.CharField(max_length=TEXT_LEN)
	order = models.PositiveSmallIntegerField();
	
	# Other model methods and meta options
	
	objects = OptionManager()

	def natural_key(self):
		return (self.text,) + self.question.natural_key()
	
	def __str__(self):
		return self.text
	
	class Meta:
		unique_together = ('question', 'text')


class BallotManager(models.Manager):
	
	def get_by_natural_key(self, ballot_id, election_id):
		return self.get(ballot_id=ballot_id, election__election_id=election_id)


class Ballot(models.Model):
	
	election = models.ForeignKey(Election)
	
	ballot_id = models.PositiveIntegerField()
	credential_hash = models.CharField(max_length=HASH_LEN)
	
	# Other model methods and meta options
	
	objects = BallotManager()

	def natural_key(self):
		return (self.ballot_id,) + self.election.natural_key()
	
	def __str__(self):
		return str(self.ballot_id)
	
	class Meta:
		unique_together = ('election', 'ballot_id')


class SideManager(models.Manager):
	
	def get_by_natural_key(self, side_id, ballot_id, election_id):
		
		return self.get(side_id=side_id, ballot__ballot_id=ballot_id,
			ballot__election__election_id=election_id)


class Side(models.Model):
	
	ballot = models.ForeignKey(Ballot)
	
	side_id = models.CharField(max_length=1, choices=SIDE_ID_CHOICES)
	permindex_hash = models.CharField(max_length=HASH_LEN)
	
	# Other model methods and meta options
	
	objects = SideManager()

	def natural_key(self):
		return (self.side_id,) + self.ballot.natural_key()
	
	def __str__(self):
		return self.side_id
	
	class Meta:
		unique_together = ('ballot', 'side_id')


class OptDataManager(models.Manager):
	
	def get_by_natural_key(self, votecode, side_id, ballot_id, election_id1,	
		question_id, election_id2):
		
		return self.get(votecode=votecode, side__side_id=side_id,
			side__ballot__ballot_id=ballot_id,
			side__ballot__election__election_id=election_id1,
			question__question_id=question_id,
			question__election__election_id=election_id2)


class OptData(models.Model):
	
	side = models.ForeignKey(Side)
	question = models.ForeignKey(Question)
	
	votecode = models.PositiveSmallIntegerField()
	receipt = models.CharField(max_length=RECEIPT_LEN)
	
	com = fields.JsonField()
	decom = fields.JsonField()
	zk1 = fields.JsonField(compressed=True)
	zk_state = fields.JsonField(compressed=True)
	
	order = models.PositiveSmallIntegerField()
	
	# Other model methods and meta options
	
	objects = OptDataManager()

	def natural_key(self):
		return (self.votecode,) + self.side.natural_key() + \
			self.question.natural_key()
	
	def __str__(self):
		return str(self.votecode)
	
	class Meta:
		unique_together = ('side', 'question', 'votecode')


class TrusteeManager(models.Manager):
	
	def get_by_natural_key(self, election, email):
		return self.get(election__election_id=election_id, email=email)


class Trustee(models.Model):
	
	election = models.ForeignKey(Election)
	
	email = models.EmailField()
	
	# Other model methods and meta options
	
	objects = TrusteeManager()

	def natural_key(self):
		return (self.email,) + self.election.natural_key()
	
	def __str__(self):
		return self.email
	
	class Meta:
		unique_together = ('election', 'email')


class Task(models.Model):
	
	task_id = models.UUIDField()
	election_id = models.CharField(max_length=8, unique=True)

