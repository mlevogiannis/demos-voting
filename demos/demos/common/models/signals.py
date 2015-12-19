# File signals.py

from django.db import IntegrityError


def pre_delete_protect_handler(sender, **kwargs):
    raise IntegrityError("Cannot delete instances of protected model '%s'" % sender.__name__)

