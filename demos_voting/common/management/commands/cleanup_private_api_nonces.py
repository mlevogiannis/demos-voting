# File: cleanup_private_api_nonces.py

from __future__ import absolute_import, division, print_function, unicode_literals

import time

from django.apps import apps
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Remove expired private API nonces."
    
    def add_arguments(self, parser):
        
        parser.add_argument('app_label', nargs=1,
            help="App label of an application to clean up private API nonces.")
        
        parser.add_argument('-l', '--local', action='store_true', dest='local', default=False,
            help="Remove only local nonces.")
        
        parser.add_argument('-r', '--remote', action='store_true', dest='remote', default=False,
            help="Remove only remote nonces.")
    
    def handle(self, *args, **options):
        
        app_config = apps.get_app_config(options['app_label'][0])
        PrivateApiNonce = app_config.get_model('PrivateApiNonce')
        
        nonces = PrivateApiNonce.objects.filter(timestamp__lt=int(time.time()))
        
        if options['local'] and not options['remote']:
            nonces = nonces.filter(type=PrivateApiNonce.TYPE_LOCAL)
        elif options['remote'] and not options['local']:
            nonces = nonces.filter(type=PrivateApiNonce.TYPE_REMOTE)
        
        nonces.delete()

