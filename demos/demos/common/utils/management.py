# File: management.py

from __future__ import division

import sys
import getpass

from django.contrib.auth.models import User as LocalUser
from django.core.management.base import BaseCommand, CommandError


# https://docs.python.org/3/library/functions.html#input
# https://docs.python.org/2/library/functions.html#raw_input
try:
    input = raw_input
except NameError:
    pass


class UserCommand(BaseCommand):
    help = 'Used to create demos users.'
    
    def __init__(self, app_config, local_apps, remote_apps, *args, **kwargs):
        
        self.app_config = app_config
        self.local_apps = local_apps
        self.remote_apps = remote_apps
        
        super(UserCommand, self).__init__(*args, **kwargs)
    
    def add_arguments(self, parser):
        
        parser.add_argument('-d', '--dump',
            action='store_true',
            dest='dump',
            default=False,
            help='Dump remote user account data to stdout'
        )
    
    def handle(self, *args, **options):
        
        RemoteUser = self.app_config.get_model('RemoteUser')
        
        max_password = RemoteUser._meta.get_field('password').max_length
        
        if options['dump']:
            for user in RemoteUser.objects.order_by('username').all():
                self.stdout.write("%s: %s" % (user.username, user.password))
            return
        
        try:
            local_users = []
            remote_users = []
            
            self.stdout.write("%s User Accounts Setup"
                % self.app_config.verbose_name)
            
            if self.local_apps:
                
                self.stdout.write("\n1. Local user accounts")
                self.stdout.write("User accounts used by the other servers to "
                    "login and use this server's web API")
                
                for username in self.local_apps:
                    self.stdout.write("\nUsername: %s" % username)
                    password = self._get_password(max_password)
                    user = self._create_user(LocalUser, username, password)
                    local_users.append(user)
            
            if self.remote_apps:
                
                self.stdout.write("\n2. Remote user accounts")
                self.stdout.write("User accounts used by this server to login "
                    "and use the other servers' web API")
                
                for username in self.remote_apps:
                    self.stdout.write("\nUsername: %s" % username)
                    password = self._get_password(max_password)
                    user = self._create_user(RemoteUser, username, password)
                    remote_users.append(user)
        
        except (KeyboardInterrupt, EOFError):
            self.stderr.write("\nOperation cancelled.")
            sys.exit(1)
    
    def _create_user(self, usermodel, username, password):
        
        try:
            user = usermodel.objects.get(username=username)
        except usermodel.DoesNotExist:
            pass
        else:
            r = ''
            while r not in ('Y', 'N'):
                r = input("Username already exists. Overwrite? [Y/N] ")
                r = r.upper()
            
            if r == 'Y':
                user.delete()
            else:
                raise KeyboardInterrupt
        
        args = {'username': username, 'password': password}
        
        if hasattr(usermodel.objects, 'create_user'):
            user = usermodel.objects.create_user(**args)
        else:
            user = usermodel.objects.create(**args)
        
        return user
    
    def _get_password(self, max_password):
        
        password = None
        
        while password is None:
            
            password = getpass.getpass('Password: ')
            password2 = getpass.getpass('Password (again): ')
            
            if password != password2:
                self.stderr.write("Error: The passwords didn't match.")
                password = None
                continue
                
            if password.strip() == "":
                self.stderr.write("Error: Blank passwords aren't allowed.")
                password = None
                continue
            
            if len(password) > max_password:
                self.stderr.write("Error: The passwords is longen than %s " \
                    "characters." % max_password)
                password = None
                continue
        
        return password

