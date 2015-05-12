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
		return urlresolvers.reverse('demos_bds:', args=[self.election_id])
	
	def __str__(self):
		return self.text


class BallotManager(models.Manager):
	
	def get_by_natural_key(self, ballot_id, election_id):
		return self.get(ballot_id=ballot_id, election__election_id=election_id)


class Ballot(models.Model):
	
	election = models.ForeignKey(Election)
	
	def ballot_path(self, filename):
		basedir = "ballots"
		election_id = self.election.election_id
		filename = "{0}.pdf".format(self.ballot_id)
		return '/'.join([basedir, election_id, filename])
	
	ballot_id = models.PositiveIntegerField()
	pdf = models.FileField(upload_to=ballot_path)
	
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
	permindex = models.CharField(max_length=PERMINDEX_LEN)
	voteurl = models.CharField(max_length=VOTEURL_LEN)
	
	# Other model methods and meta options
	
	objects = SideManager()

	def natural_key(self):
		return (self.side_id,) + self.ballot.natural_key()
	
	def __str__(self):
		return self.side_id
	
	class Meta:
		unique_together = ('ballot', 'side_id')


class TrusteeManager(models.Manager):
	
	def get_by_natural_key(self, email, election_id):
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

