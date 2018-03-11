from __future__ import absolute_import, division, print_function, unicode_literals

import sys

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from six.moves import input

from demos_voting.base.models import HTTPSignatureKey


class Command(BaseCommand):
    help = "Used to create the system's users."
    requires_migrations_checks = True

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.user_model = get_user_model()
        # Generate the list of the users that must me be handled. Users that
        # are installed on the same server share the same key, so group them
        # accordingly.
        app_labels = {'ballot_distributor', 'bulletin_board', 'election_authority', 'vote_collector'}
        installed_app_labels = set()
        for app_label in app_labels:
            if apps.is_installed('demos_voting.%s' % app_label):
                installed_app_labels.add(app_label)
        self.usernames_list = sorted([username] for username in app_labels - installed_app_labels)
        if len(installed_app_labels) > 1:
            self.usernames_list.append(sorted(app_labels & installed_app_labels))

    def add_arguments(self, parser):
        parser.add_argument(
            '--dump',
            action='store_true',
            dest='dump',
            default=False,
            help="Dumps the system users' keys to stdout.",
        )

    def handle(self, *args, **options):
        if options['dump']:
            key_ids = [username for usernames in self.usernames_list for username in usernames]
            for key_obj in HTTPSignatureKey.objects.filter(key_id__in=key_ids):
                self.stdout.write("%s: %s" % (key_obj.key_id, key_obj.key))
        else:
            try:
                for usernames in self.usernames_list:
                    key = input("%s: " % ','.join(usernames))
                    if key.strip() == '':
                        continue
                    for username in usernames:
                        try:
                            user = self.user_model.objects.get(username=username)
                        except self.user_model.DoesNotExist:
                            user = self.user_model.objects.create_user(username=username)
                        HTTPSignatureKey.objects.update_or_create(user=user, key_id=username, defaults={'key': key})
            except (KeyboardInterrupt, EOFError):
                self.stderr.write("\nOperation cancelled.")
                sys.exit(1)
