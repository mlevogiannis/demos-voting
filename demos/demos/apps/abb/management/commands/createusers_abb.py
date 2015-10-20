# File: users.py

from django.apps import apps
from demos.common.utils.management import UserCommand


class Command(UserCommand):
	
	def __init__(self, *args, **kwargs):
		
		super(Command, self).__init__(
			local_apps=['ea', 'vbb'],
			remote_apps=['ea'],
			app_config=apps.get_app_config('abb'),
			*args, **kwargs
		)
	
