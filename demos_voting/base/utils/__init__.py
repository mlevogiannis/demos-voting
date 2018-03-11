from __future__ import absolute_import, division, print_function, unicode_literals

import hashlib

from django.apps import apps
from django.contrib.auth.hashers import PBKDF2PasswordHasher

from six.moves import range

installed_app_labels = []
for app_label in ['ballot_distributor', 'bulletin_board', 'election_authority', 'vote_collector']:
    if apps.is_installed('demos_voting.%s' % app_label):
        installed_app_labels.append(app_label)


def get_site_url(request):
    return request.META['SCRIPT_NAME'] or '/'


def get_range_in_chunks(range_length, chunk_count):
    q, r = divmod(range_length, chunk_count)
    range_chunks = []
    for i in range(chunk_count):
        range_start = q * i + min(i, r)
        range_stop = q * (i + 1) + min((i + 1), r)
        if range_start >= range_stop:
            break
        range_chunks.append((range_start, range_stop))
    return range_chunks


class PBKDF2SHA512Hasher(PBKDF2PasswordHasher):
    algorithm = "pbkdf2_sha512"
    iterations = 200000
    digest = hashlib.sha512

    def summary(self, encoded):
        algorithm, iterations, salt, hash = encoded.split('$', 3)
        assert algorithm == self.algorithm
        return {'algorithm': algorithm, 'iterations': int(iterations), 'salt': salt, 'hash': hash}


hasher = PBKDF2SHA512Hasher()
