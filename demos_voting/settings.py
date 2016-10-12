# -*- encoding: utf-8 -*-

"""
Django settings for demos_voting project.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

from __future__ import absolute_import, division, print_function, unicode_literals


# Quick-start settings
# https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = ''

# SECURITY WARNING: don't run with debug/development turned on in production!
DEBUG = False
DEVELOPMENT = False

if DEVELOPMENT:
    DEBUG = True

ALLOWED_HOSTS = [
    'www.example.com',
]


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)

import os

# BASE_DIR should be read-only (e.g. /usr/local/share/demos-voting/).
BASE_DIR = ''

# DATA_DIR must be read/write (e.g. /var/lib/demos-voting/).
DATA_DIR = ''

if DEVELOPMENT:
    BASE_DIR = DATA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Configuration for running behind a proxy

FORCE_SCRIPT_NAME = None

USE_X_FORWARDED_HOST = False
USE_X_FORWARDED_PROTO = False

if USE_X_FORWARDED_PROTO:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'demos_voting.common',
]

MIDDLEWARE_CLASSES = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'demos_voting.common.middleware.PrivateApiMiddleware',
]

ROOT_URLCONF = 'demos_voting.urls'
WSGI_APPLICATION = 'demos_voting.wsgi.application'


# Templates
# https://docs.djangoproject.com/en/1.8/ref/settings/#templates

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
            'loaders': [
                ('django.template.loaders.cached.Loader', [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ]),
            ],
        },
    },
]

if DEVELOPMENT:
    TEMPLATES[0]['APP_DIRS'] = True
    del TEMPLATES[0]['OPTIONS']['loaders']


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'demos_voting',
        'USER': 'demos_voting',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '5432',
    }
}


# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

from django.utils.translation import ugettext_lazy as _

LANGUAGES = [
    ('el', _('Greek')),
    ('en', _('English')),
]

LANGUAGE_CODE = 'en-us'

USE_TZ = True
TIME_ZONE = 'Europe/Athens'

USE_I18N = True
USE_L10N = True

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'demos_voting/common/locale'),
]


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')


# Media files (generated or user-uploaded)
# https://docs.djangoproject.com/en/1.8/topics/files/

# SECURITY WARNING: Do NOT configure your web server to serve the files in
# MEDIA_ROOT under the URL MEDIA_URL. Direct access must be restricted, so
# files will be served by the web application.

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(DATA_DIR, 'media')


# Sending email
# https://docs.djangoproject.com/en/1.8/topics/email/

EMAIL_HOST = ''
EMAIL_PORT = 587
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_USE_TLS = True

DEFAULT_FROM_EMAIL = ''

SERVER_EMAIL = ''
EMAIL_SUBJECT_PREFIX = '[DEMOS Voting] '

ADMINS = [
    ('Admin', 'admin@example.com'),
]

if DEVELOPMENT:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# Security Middleware
# https://docs.djangoproject.com/en/1.8/ref/middleware/#module-django.middleware.security

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_SSL_HOST = None
SECURE_SSL_REDIRECT = True
#SECURE_HSTS_SECONDS = 31536000
#SECURE_HSTS_INCLUDE_SUBDOMAINS = True

if DEVELOPMENT:
    SECURE_BROWSER_XSS_FILTER = False
    SECURE_CONTENT_TYPE_NOSNIFF = False
    SECURE_SSL_HOST = None
    SECURE_SSL_REDIRECT = False
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False

CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

if DEVELOPMENT:
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False


# Logging
# https://docs.djangoproject.com/en/1.8/topics/logging/

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'syslog': {
            'level': 'INFO',
            'class': 'logging.handlers.SysLogHandler',
            'address': '/dev/log',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        },
    },
    'loggers': {
        'root': {
            'handlers': ['syslog']
            },
        'django': {
            'handlers': ['mail_admins', 'syslog'],
            'level': 'INFO',
        },
        'demos_voting': {
            'handlers': ['mail_admins', 'syslog'],
            'level': 'INFO',
        },
    },
}

if DEVELOPMENT:
    
    LOGGING['handlers'] = {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    }
    
    LOGGING['loggers'] = {
        'root': {
            'handlers': ['console']
        },
        'django': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'demos_voting': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    }


# DEMOS Voting configuration

# DEMOS_VOTING_APPS: One or more of ['ea', 'bds', 'abb', 'vbb']. Warning: The
# apps must be isolated (with regard to data storage, access to the server,
# etc) in order to protect the voter's privacy. Do NOT install multiple apps
# on the same production server. This feature is intended to be used only for
# development purposes.

DEMOS_VOTING_APPS = []

INSTALLED_APPS += ['demos_voting.apps.%s' % app for app in DEMOS_VOTING_APPS]
LOCALE_PATHS += [os.path.join(BASE_DIR, 'demos_voting/apps/%s/locale' % app) for app in DEMOS_VOTING_APPS]

# DEMOS_VOTING_URLS: The URLs by which the apps are served. Always use HTTPS.

DEMOS_VOTING_URLS = {
    'ea':  'https://www.example.com/demos-voting/ea/',
    'bds': 'https://www.example.com/demos-voting/bds/',
    'abb': 'https://www.example.com/demos-voting/abb/',
    'vbb': 'https://www.example.com/demos-voting/vbb/',
}

# DEMOS_VOTING_PRIVATE_API_URLS: Same as DEMOS_VOTING_URLS, but used only for
# private API requests. It is recommended that these URLs are accessible only
# through a private network.

DEMOS_VOTING_PRIVATE_API_URLS = {
    'ea':  'https://demos-voting-ea.example.local/',
    'bds': 'https://demos-voting-bds.example.local/',
    'abb': 'https://demos-voting-abb.example.local/',
    'vbb': 'https://demos-voting-vbb.example.local/',
}

# DEMOS_VOTING_PRIVATE_API_VERIFY_SSL: Verify SSL certificates for private API
# requests (enabled by default). See:
# http://docs.python-requests.org/en/latest/user/advanced/#ssl-cert-verification

DEMOS_VOTING_PRIVATE_API_VERIFY_SSL = True

# DEMOS_VOTING_PRIVATE_API_NONCE_TIMEOUT: To avoid the need to retain an
# infinite number of nonces, restrict the time period after which a request
# with an old timestamp is rejected. The client's and server's clocks must be
# synchronized. The value is in seconds.

DEMOS_VOTING_PRIVATE_API_NONCE_TIMEOUT = 300

# DEMOS_VOTING_BATCH_SIZE: Controls how many objects (e.g. ballots) are
# processed in one batch.

DEMOS_VOTING_BATCH_SIZE = 100

# DEMOS_VOTING_CA_*: (ea only) Certificate authority configuration. If both
# CA_CERT_FILE and CA_PKEY_FILE are not provided, self-signed certificates
# will be generated. CA_PKEY_PASSPHRASE is optional.

DEMOS_VOTING_CA_CERT_FILE = ''
DEMOS_VOTING_CA_PKEY_FILE = ''
DEMOS_VOTING_CA_PKEY_PASSPHRASE = ''

# DEMOS_VOTING_LONG_VOTECODE_HASH_REUSE_SALT: (ea only) Use the same salt value
# for all long votecode hashes of each ballot part's question. This can greatly
# improve vbb's performance for questions with many options.

DEMOS_VOTING_LONG_VOTECODE_HASH_REUSE_SALT = False

# DEMOS_VOTING_MAX_*: The maximum number of ballots, questions per referendum,
# options per question, parties per election and candidates per party.

DEMOS_VOTING_MAX_BALLOTS = 10000
DEMOS_VOTING_MAX_REFERENDUM_QUESTIONS = 50
DEMOS_VOTING_MAX_REFERENDUM_OPTIONS = 50
DEMOS_VOTING_MAX_ELECTION_PARTIES = 50
DEMOS_VOTING_MAX_ELECTION_CANDIDATES = 50


# Celery configuration
# http://docs.celeryproject.org/en/latest/getting-started/brokers/index.html

INSTALLED_APPS += ['kombu.transport.django']

BROKER_URL = 'django://'
CELERY_RESULT_BACKEND = 'db+postgresql://%(USER)s:%(PASSWORD)s@%(HOST)s:%(PORT)s/%(NAME)s' % DATABASES['default']

CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']

