# File: users.py

from django.apps import apps
from demos.common.utils.management import UserCommand


class Command(UserCommand):
    
    def __init__(self, *args, **kwargs):
        
        super(Command, self).__init__(
            local_apps=['abb'],
            remote_apps=['bds', 'abb', 'vbb'],
            app_config=apps.get_app_config('ea'),
            *args, **kwargs
        )
    
