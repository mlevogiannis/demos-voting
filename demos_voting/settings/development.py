from __future__ import absolute_import, division, print_function, unicode_literals

from demos_voting.settings.base import *

DATA_DIR = BASE_DIR

SECRET_KEY = 'secret-key'

DEBUG = True

ALLOWED_HOSTS = [
    '*',
]

INTERNAL_IPS = [
    'localhost',
    '127.0.0.1',
    '[::1]',
]

# Application definition

INSTALLED_APPS[:0] = [
    'demos_voting.ballot_distributor',
    'demos_voting.bulletin_board',
    'demos_voting.election_authority',
    'demos_voting.vote_collector',
    'debug_toolbar',
]

MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'demos_voting',
        'USER': 'demos_voting',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    },
}

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = '/static/'

# Managing files
# https://docs.djangoproject.com/en/1.11/topics/files/

MEDIA_ROOT = os.path.join(DATA_DIR, 'media')

# Sending email
# https://docs.djangoproject.com/en/1.11/topics/email/

EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH = os.path.join(DATA_DIR, 'emails')

# Logging
# https://docs.djangoproject.com/en/1.11/topics/logging/

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'root': {
            'handlers': ['console']
        },
        'django': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
        'django.db.backends': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False,
        },
        'demos_voting': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    },
}

# django-debug-toolbar
# https://github.com/jazzband/django-debug-toolbar/

DEBUG_TOOLBAR_CONFIG = {
    'JQUERY_URL': None
}

# Celery
# http://docs.celeryproject.org/en/latest/django/index.html

CELERY_BROKER_URL = 'redis://'

# DEMOS Voting
# See 'settings/base.py' for more information.

DEMOS_VOTING_URLS = {
    'ballot_distributor': 'http://localhost:8000/ballot-distributor/',
    'bulletin_board': 'http://localhost:8000/bulletin-board/',
    'election_authority': 'http://localhost:8000/election-authority/',
    'vote_collector': 'http://localhost:8000/vote-collector/',
}
