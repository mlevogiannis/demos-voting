# File: create_private_api_users.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.utils.six.moves import input


class Command(BaseCommand):
    help = "Create private API users."

    def add_arguments(self, parser):

        parser.add_argument('app_label', nargs=1,
            help="App label of an application to create private API users.")

        parser.add_argument('-d', '--dump', action='store_true', dest='dump', default=False,
            help="Dump all pre-shared keys to stdout.")

    def handle(self, *args, **options):

        app_config = apps.get_app_config(options['app_label'][0])
        PrivateApiUser = app_config.get_model('PrivateApiUser')

        self.stdout.write("Pre-shared keys for '%s'." % app_config.verbose_name)

        if options['dump']:
            for app_label in PrivateApiUser.APP_DEPENDENCIES[app_config.label]:
                self.stdout.write("%s: " % app_label, ending='')
                try:
                    preshared_key = PrivateApiUser.objects.get(app_label=app_label).preshared_key
                    self.stdout.write("%s" % preshared_key)
                except PrivateApiUser.DoesNotExist:
                    self.stdout.flush()
                    self.stderr.write("not found")
            return

        min_length = 16
        max_length = PrivateApiUser._meta.get_field('preshared_key').max_length

        try:
            for app_label in PrivateApiUser.APP_DEPENDENCIES[app_config.label]:
                try:

                    while True:
                        preshared_key = input("%s: " % app_label)

                        if len(preshared_key) < min_length:
                            self.stderr.write("Key is too short (min_length is %d)" % min_length)
                            continue

                        if len(preshared_key) > max_length:
                            self.stderr.write("Key is too long (max_length is %d)" % max_length)
                            continue

                        break

                    try:
                        user = PrivateApiUser.objects.get(app_label=app_label)

                        r = ''
                        while r not in ('Y', 'N'):
                            r = input("Already exists. Overwrite? [Y/N] ").upper()

                        if r == 'Y':
                            user.preshared_key = preshared_key
                            user.save(update_fields=['preshared_key'])

                    except PrivateApiUser.DoesNotExist:
                        PrivateApiUser.objects.create(app_label=app_label, preshared_key=preshared_key)

                except EOFError:
                    self.stderr.write("skipped")
                    continue

        except KeyboardInterrupt:
            self.stdout.write("")
            raise CommandError("aborted")

